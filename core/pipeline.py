# -*- coding: utf-8 -*-
"""集成联调主流程:导入 -> 识别 -> 卡片 -> 回应 -> 导出。

识别引擎使用 core/analysis(规则初筛 + DeepSeek 模型增强);
导出使用 scripts/render(Node:pureimage + pdfkit)。
"""
from __future__ import absolute_import, unicode_literals

import json
import os

from .analysis import create_engine
from .analysis.config import config as _config
from .card.model import build_card
from .export.markdown import export_markdown
from .export.renderer import export_card_and_pdf
from .parser import parse_wechat_file
from .response.engine import generate_response, generate_response_with_api


def _ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)


def _pick_best(results):
    if not results:
        return None
    return max(results, key=lambda r: r.depth_score)


class PipelineResult(object):
    def __init__(self, session, analysis, card, response, exports):
        self.session = session
        self.analysis = analysis
        self.card = card
        self.response = response
        self.exports = exports

    def summary_dict(self):
        return {
            "session_id": self.session.session_id,
            "peer": self.session.peer,
            "message_count": self.session.message_count,
            "depth_score": self.analysis.depth_score,
            "is_deep": self.analysis.is_deep,
            "dimensions": self.analysis.dimensions,
            "tags": self.analysis.tags,
            "summary": self.analysis.summary,
            "response_model": self.response.get("model"),
            "exports": dict(self.exports),
        }


def run_pipeline(txt_path, out_dir=None, use_api=None, model=None,
                 me_nickname=None):
    """全链路执行,返回 PipelineResult。"""
    session = parse_wechat_file(txt_path, me_nickname=me_nickname)
    provider = "deepseek" if (use_api is not False and _config.is_configured) \
        else "mock"
    engine = create_engine(provider=provider)
    results = engine.analyze_session(session.to_dict(), model=model)
    analysis = _pick_best(results)
    if analysis is None:
        raise ValueError("识别结果为空,无法继续")
    card = build_card(analysis, session)

    if use_api is False or (use_api is None and not _config.is_configured):
        response = generate_response(analysis, session)
    else:
        response = generate_response_with_api(
            analysis, session, model=model or _config.default_model)

    exports = {}
    if out_dir:
        _ensure_dir(out_dir + os.sep)
        base = os.path.join(out_dir, session.session_id)
        md_path = base + ".md"
        export_markdown(session, analysis, response, out_path=md_path)
        exports["markdown"] = md_path
        try:
            png_path = base + ".png"
            pdf_path = base + ".pdf"
            export_card_and_pdf(
                session, analysis, response, png_path, pdf_path, card=card)
            exports["png"] = png_path
            exports["pdf"] = pdf_path
        except Exception as exc:
            exports["render_error"] = str(exc)
    return PipelineResult(session, analysis, card, response, exports)


def run_demo(txt_path, out_dir, use_api=None):
    result = run_pipeline(txt_path, out_dir=out_dir, use_api=use_api)
    print(json.dumps(result.summary_dict(), ensure_ascii=False, indent=2))
    return result

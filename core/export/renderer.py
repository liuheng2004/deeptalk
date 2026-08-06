# -*- coding: utf-8 -*-
"""PNG / PDF 导出:委托 Node 渲染器(scripts/render)。

Node 渲染器基于 pureimage + pdfkit,天然支持中文;
Python 侧负责数据组装与调用,失败时给出明确错误。
"""
from __future__ import absolute_import, unicode_literals

import json
import os
import subprocess
import tempfile


def _render_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    # core/export/renderer.py -> core/export -> 项目根(core 的父目录)
    root = os.path.dirname(os.path.dirname(here))
    return os.path.join(root, "scripts", "render")


def _find_node():
    for name in ("node", "node.exe"):
        try:
            p = subprocess.Popen(
                [name, "--version"], stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL)
            p.communicate()
            if p.returncode == 0:
                return name
        except Exception:
            pass
    return None


def _write_payload(data):
    fd, path = tempfile.mkstemp(suffix=".json", prefix="deeptalk-render-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def _call_renderer(payload, out_png, out_pdf):
    node = _find_node()
    if node is None:
        raise RuntimeError("Node.js 不可用,无法渲染 PNG/PDF")
    render_dir = _render_dir()
    script = os.path.join(render_dir, "render_exports.js")
    if not os.path.exists(script):
        raise RuntimeError("渲染脚本缺失: " + script)
    payload["out_png"] = out_png
    payload["out_pdf"] = out_pdf
    payload["font"] = payload.get("font") or r"C:\Windows\Fonts\simhei.ttf"
    payload_path = _write_payload(payload)
    try:
        proc = subprocess.Popen(
            [node, script, payload_path],
            cwd=render_dir,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate(timeout=180)
        if proc.returncode != 0:
            raise RuntimeError(
                "渲染失败: " + (err or out).decode("utf-8", "replace")[:500])
    finally:
        try:
            os.remove(payload_path)
        except OSError:
            pass


def export_card_and_pdf(session, analysis, response, out_png, out_pdf,
                        card=None, font_path=None):
    """渲染分享卡片 PNG 与归档 PDF(一次 Node 调用)。"""
    from ..card.model import build_card
    card = card or build_card(analysis, session)
    payload = {
        "font": font_path or r"C:\Windows\Fonts\simhei.ttf",
        "peer": session.peer or "对方",
        "date_text": card.date_text,
        "relative_text": card.relative_text,
        "title": card.title,
        "tags": card.tags,
        "golden_quotes": [q["text"] for q in card.golden_quotes],
        "depth_score": analysis.depth_score,
        "start_time": analysis.start_time,
        "created_at": session.created_at,
        "summary": analysis.summary,
        "response_text": response["text"],
        "messages": [
            {"sender": m.sender, "timestamp": m.timestamp,
             "content": m.content}
            for m in session.messages],
    }
    _call_renderer(payload, out_png, out_pdf)
    return card

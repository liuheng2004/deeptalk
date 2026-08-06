# -*- coding: utf-8 -*-
"""回应生成实现。

优先调用 DeepSeek(复用 core/analysis 的 ModelProvider 抽象);
无 API Key 或调用失败时使用本地模板,保证演示离线可用。
"""
from __future__ import absolute_import, unicode_literals

import json


def _relative_date(iso_text, now=None):
    import datetime
    import re
    if not iso_text:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", iso_text)
    if not m:
        return ""
    then = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    today = now or datetime.date.today()
    if isinstance(today, datetime.datetime):
        today = today.date()
    days = (today - then).days
    if days < 0:
        return ""
    if days == 0:
        return "今天"
    if days < 30:
        return "%d 天前" % days
    if days < 365:
        return "%d 个月前" % max(1, days // 30)
    return "%d 年前" % (days // 365)


def generate_response(analysis, session=None, persona="知心朋友"):
    """本地模板生成回应(离线)。"""
    peer = (session.peer if session else None) or "对方"
    score = analysis.depth_score
    tags = "、".join(analysis.tags or [])
    quote = ""
    if analysis.golden_quotes:
        q = analysis.golden_quotes[0]
        quote = q.get("text") if isinstance(q, dict) else q
    rel = _relative_date(analysis.start_time)
    date_part = ("(%s)" % rel) if rel else ""
    lines = [
        "我看到了一段很真实的对话%s。" % date_part,
    ]
    if tags:
        lines.append("这段交流里,有「%s」的影子。" % tags)
    if quote:
        lines.append("尤其是那句「%s」,让人很难不被打动。" % quote)
    if score >= 80:
        lines.append("它值得被好好收起来——不是作为谈资,而是作为你们彼此懂得的证据。")
    elif score >= 60:
        lines.append("这大概就是那种会留在记忆里的对话,值得被记下来。")
    else:
        lines.append("也许它看起来平常,但生活里最珍贵的往往就是这些日常。")
    lines.append("如果你愿意,可以把它存成一张卡片,或写封信给%s。" % peer)
    return {
        "text": "\n".join(lines),
        "model": "rule-based",
        "persona": persona,
    }


def generate_response_with_api(analysis, session=None, persona="知心朋友",
                               model=None, api_key=None, base_url=None,
                               timeout=60):
    """调用 DeepSeek 生成回应;失败时回退本地模板。"""
    from ..analysis.config import config as _config
    from ..analysis.model_provider import create_provider
    key = api_key or _config.api_key
    model = model or _config.default_model
    if not key:
        return generate_response(analysis, session, persona)
    peer = (session.peer if session else None) or "对方"
    try:
        provider = create_provider("deepseek")
        payload = {
            "peer": peer,
            "depth_score": analysis.depth_score,
            "tags": analysis.tags,
            "summary": analysis.summary,
            "golden_quotes": [
                q.get("text") if isinstance(q, dict) else q
                for q in analysis.golden_quotes],
        }
        prompt = (
            "你是一个温暖、克制、有洞察力的第三方观察者。请以「%s」的身份,"
            "给这段深度对话写一段 80-150 字的回应,像朋友一样共情,"
            "但不要居高临下,不要评判。直接输出回应文本,不要任何前缀。"
            "对话信息:%s" % (persona, json.dumps(payload, ensure_ascii=False)))
        text = provider.chat(
            messages=[
                {"role": "system", "content":
                 "你是 DeepTalk 内置的温暖回应引擎。"},
                {"role": "user", "content": prompt},
            ],
            model=model)
        text = (text or "").strip()
        if not text:
            raise ValueError("empty response")
        return {"text": text, "model": model, "persona": persona}
    except Exception:
        return generate_response(analysis, session, persona)

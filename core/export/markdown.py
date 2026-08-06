# -*- coding: utf-8 -*-
"""Markdown 导出(带 YAML front matter,Obsidian 友好)。"""
from __future__ import absolute_import, unicode_literals

import io
import re


def _safe_quote(s):
    return (s or "").replace('"', '\\"')


def _fmt_date(iso_text):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", iso_text or "")
    return m.group(0) if m else (iso_text or "")


def export_markdown(session, analysis, response, out_path=None):
    """生成 Markdown 文档。返回文本。"""
    tags = analysis.tags or []
    quotes = analysis.golden_quotes or []
    fm = [
        "---",
        "title: %s" % _safe_quote(
            "与%s的深度对话" % session.peer),
        "date: %s" % _fmt_date(analysis.start_time),
        "peer: %s" % _safe_quote(session.peer),
        "depth_score: %d" % int(round(analysis.depth_score)),
        "tags: [%s]" % ", ".join(tags),
        "session_id: %s" % session.session_id,
        "---",
        "",
    ]
    body = [
        "## 对话摘要",
        "",
        analysis.summary,
        "",
        "## AI 第三方回应",
        "",
        response["text"],
        "",
        "## 金句",
        "",
    ]
    for q in quotes[:3]:
        body.append("- %s" % q["text"])
    body += ["", "## 完整对话", ""]
    for m in session.messages:
        sender = "我" if m.sender == "me" else m.sender
        ts = _fmt_date(m.timestamp) + " " + re.sub(
            r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}).*", r"\2",
            m.timestamp or "")
        label = sender or "对方"
        body.append("### %s · %s" % (label, ts))
        body.append("")
        body.append(m.content)
        body.append("")
    text = "\n".join(fm + body)
    if out_path:
        with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return text

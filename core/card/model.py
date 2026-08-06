# -*- coding: utf-8 -*-
"""卡片数据模型。"""
from __future__ import absolute_import, unicode_literals

import re


class Card(object):
    """一张分享卡片的数据。"""

    def __init__(self, title, peer, date_text, relative_text, tags,
                 golden_quotes, depth_score, session_id):
        self.title = title
        self.peer = peer
        self.date_text = date_text
        self.relative_text = relative_text
        self.tags = tags
        self.golden_quotes = golden_quotes
        self.depth_score = depth_score
        self.session_id = session_id

    def to_dict(self):
        return {
            "title": self.title,
            "peer": self.peer,
            "date_text": self.date_text,
            "relative_text": self.relative_text,
            "tags": list(self.tags),
            "golden_quotes": [q["text"] for q in self.golden_quotes],
            "depth_score": self.depth_score,
            "session_id": self.session_id,
        }


def _fmt_date(iso_text):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", iso_text or "")
    if not m:
        return ""
    return "%s.%s.%s" % (m.group(1), m.group(2), m.group(3))


def _relative_date(iso_text, now=None):
    import datetime
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", iso_text or "")
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


def build_card(analysis, session=None):
    """由识别结果构造卡片数据。"""
    peer = (session.peer if session else None) or "对方"
    tags = analysis.tags or []
    quotes = analysis.golden_quotes or []
    if not quotes:
        quotes = [{"text": analysis.summary, "message_id": ""}]
    title = "深夜长谈" if analysis.depth_score >= 60 else "一段对话"
    return Card(
        title=title,
        peer=peer,
        date_text=_fmt_date(analysis.start_time),
        relative_text=_relative_date(analysis.start_time),
        tags=tags,
        golden_quotes=quotes,
        depth_score=analysis.depth_score,
        session_id=analysis.session_id,
    )

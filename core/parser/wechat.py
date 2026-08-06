# -*- coding: utf-8 -*-
"""微信「邮件发送聊天记录」txt 解析器。

规格:docs/guides/parser-spec.md
契约:docs/contracts/session.schema.json
"""
from __future__ import absolute_import, unicode_literals

import hashlib
import io
import re

# 东八区偏移,输出 ISO8601 用
TZ_OFFSET = "+08:00"

_TIME_LINE_RE = re.compile(
    r"^(?P<date>\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?|上午\s*\d{1,2}:\d{2}|下午\s*\d{1,2}:\d{2})\s+"
    r"(?P<nick>.+)$"
)
_TIME_ONLY_RE = re.compile(
    r"^(?P<time>\d{1,2}:\d{2}(?::\d{2})?|上午\s*\d{1,2}:\d{2}|下午\s*\d{1,2}:\d{2})\s+"
    r"(?P<nick>.+)$"
)

_SYSTEM_PATTERNS = [
    re.compile(r"^(.+)\s+撤回了一条消息$"),
    re.compile(r"^(.{1,20})\s+拍了拍.{0,20}$"),
    re.compile(r"^你已添加了.+，现在可以开始聊天了。$"),
    re.compile(r"^.+邀请你加入了群聊.+$"),
    re.compile(r"^以上是打招呼的内容$"),
    re.compile(r"^你通过.+添加了.+$"),
]

_TITLE_LINE = "消息记录"


class Message(object):
    """会话内一条消息。"""

    def __init__(self, mid, sender, content, timestamp, msg_type="text",
                 inferred_time=False, quote_of=None):
        self.id = mid
        self.sender = sender
        self.content = content
        self.timestamp = timestamp
        self.type = msg_type
        self.inferred_time = inferred_time
        self.quote_of = quote_of

    def to_dict(self):
        d = {
            "id": self.id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp,
            "inferred_time": self.inferred_time,
        }
        if self.type != "text":
            d["type"] = self.type
        if self.quote_of:
            d["quote_of"] = self.quote_of
        return d


class ChatSession(object):
    """解析后的会话模型,字段对齐 session.schema.json。"""

    def __init__(self, session_id, peer, created_at, messages,
                 updated_at=None, source="wechat-email-txt",
                 message_count=None, note=None):
        self.session_id = session_id
        self.peer = peer
        self.created_at = created_at
        self.updated_at = updated_at
        self.source = source
        self.message_count = message_count if message_count is not None else len(messages)
        self.note = note
        self.messages = messages

    def to_dict(self):
        d = {
            "session_id": self.session_id,
            "peer": self.peer,
            "created_at": self.created_at,
            "source": self.source,
            "message_count": self.message_count,
            "messages": [m.to_dict() for m in self.messages],
        }
        if self.updated_at:
            d["updated_at"] = self.updated_at
        if self.note:
            d["note"] = self.note
        return d


def _strip_bom(text):
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def _normalize_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_blocks(lines):
    """按空行切分消息块;连续空行视为单个分隔;跳过空块。"""
    blocks = []
    current = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _parse_header(lines):
    """阶段 A:解析元信息头。

    - 若文件首行即时间行,则无头,全部为消息块。
    - 首行可为固定标题行「消息记录」。
    - 元信息头为标题行之后、首个空行之前的全部连续行。
    返回 (header, 消息块列表)。
    """
    header = {}
    if not lines:
        return header, []
    if _TIME_LINE_RE.match(lines[0].strip()) or _TIME_ONLY_RE.match(lines[0].strip()):
        return header, _split_blocks(lines)

    idx = 0
    if lines[0].strip() == _TITLE_LINE:
        # 标题行后通常直接跟空行,再进入元信息头
        idx = 1
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1

    header_lines = []
    rest_lines = []
    for i in range(idx, len(lines)):
        line = lines[i]
        if line.strip() == "":
            rest_lines = lines[i + 1:]
            break
        header_lines.append(line)
    else:
        rest_lines = []

    for line in header_lines:
        for sep in (":", "："):
            if sep in line:
                key, _, value = line.partition(sep)
                header[key.strip()] = value.strip()
                break
    return header, _split_blocks(rest_lines)


def _parse_datetime(iso_text):
    """'YYYY-M-D H:MM:SS' -> 可比较的 (y,mo,d,h,mi,s) 元组。"""
    m = re.match(
        r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?$",
        iso_text.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)),
            int(m.group(4)), int(m.group(5)), int(m.group(6) or 0))


def _parse_header_time(text):
    """头字段 '开始时间' / '结束时间' -> ISO8601(+08:00)。"""
    t = _parse_datetime(text)
    if t is None:
        return None
    return _format_iso(*t)


def _parse_time_value(text):
    """'9:30' / '09:30:00' / '上午 9:30' / '下午1:05' -> (h, m, s)。"""
    text = text.strip()
    period = None
    if text.startswith("上午"):
        period = "am"
        text = text[2:].strip()
    elif text.startswith("下午"):
        period = "pm"
        text = text[2:].strip()
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", text)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    ss = int(m.group(3) or 0)
    if period == "pm":
        if hh != 12:
            hh += 12
    elif period == "am":
        if hh == 12:
            hh = 0
    if hh > 23 or mm > 59 or ss > 59:
        return None
    return (hh, mm, ss)


def _format_iso(y, mo, d, hh, mm, ss):
    return "%04d-%02d-%02dT%02d:%02d:%02d%s" % (y, mo, d, hh, mm, ss, TZ_OFFSET)


def _system_match(line):
    """返回 (msg_type, sender) 或 None。"""
    for pat in _SYSTEM_PATTERNS:
        m = pat.match(line.strip())
        if m:
            if pat.groups:
                return "system", m.group(1)
            return "system", None
    return None


def _quote_match(lines):
    first = lines[0].strip()
    if not first.startswith("「") or "」" not in first:
        return None
    quoted = first[1:first.index("」")].strip()
    rest = [l.rstrip() for l in lines[1:]]
    reply = "\n".join(rest).strip()
    return quoted, reply


def _normalize_text(s):
    return re.sub(r"[\s，。！？、,.!?]+", "", s)


def _resolve_quote_of(quoted, messages):
    target = _normalize_text(quoted)
    for m in reversed(messages):
        cand = _normalize_text(m.content)
        if cand == target or target in cand or cand in target:
            return m.id
    return None


def _voip_text(lines):
    """检测 [语音] + 转写。返回 (msg_type, content, note) 或 None。"""
    first = lines[0].strip()
    if first != "[语音]":
        return None
    rest = [l.rstrip() for l in lines[1:] if l.strip()]
    if not rest:
        return ("system", "[语音]", "无转写文本")
    second = rest[0]
    for prefix in ("已转文字：", "已转文字:"):
        if second.startswith(prefix):
            return ("voip_text", second[len(prefix):].strip(), None)
    return ("voip_text", second.strip(), None)


def parse_wechat_text(text, me_nickname=None):
    """解析微信导出文本,返回 ChatSession。"""
    text = _strip_bom(_normalize_newlines(text))
    lines = text.split("\n")
    header, blocks = _parse_header(lines)

    messages = []
    note_parts = []
    last_date = None
    last_ts = None
    last_sender = None
    nicknames = []

    for block in blocks:
        if not block:
            continue

        content_lines = [l.rstrip() for l in block]
        while content_lines and content_lines[0].strip() == "":
            content_lines.pop(0)
        while content_lines and content_lines[-1].strip() == "":
            content_lines.pop()
        if not content_lines:
            continue

        explicit = False
        ts = last_ts
        sender = last_sender

        tm = _TIME_LINE_RE.match(content_lines[0].strip())
        if tm:
            date_parts = re.split(r"[-/]", tm.group("date"))
            y, mo, d = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
            tv = _parse_time_value(tm.group("time"))
            nick = tm.group("nick").strip()
            if tv is not None:
                ts = _format_iso(y, mo, d, tv[0], tv[1], tv[2])
                last_date = (y, mo, d)
                last_ts = ts
                last_sender = nick
                sender = nick
                nicknames.append(nick)
                explicit = True
                content_lines = content_lines[1:]
        else:
            tonly = _TIME_ONLY_RE.match(content_lines[0].strip())
            if tonly:
                tv = _parse_time_value(tonly.group("time"))
                nick = tonly.group("nick").strip()
                if tv is not None and last_date is not None:
                    y, mo, d = last_date
                    ts = _format_iso(y, mo, d, tv[0], tv[1], tv[2])
                    last_ts = ts
                    last_sender = nick
                    sender = nick
                    nicknames.append(nick)
                    explicit = True
                    note_parts.append("存在省略日期的时间行,按前文日期回填")
                    content_lines = content_lines[1:]

        # 类型判定:system -> voip_text -> quote -> text
        msg_type = "text"
        content = "\n".join(content_lines).strip()
        quote_of = None
        local_note = None

        sys_hit = _system_match(content_lines[0])
        if sys_hit:
            msg_type, subj = sys_hit
            if subj:
                sender = subj
                nicknames.append(subj)
        else:
            vt = _voip_text(content_lines)
            if vt:
                msg_type, content, local_note = vt
            else:
                q = _quote_match(content_lines)
                if q:
                    quoted, reply = q
                    msg_type = "quote"
                    content = reply
                    quote_of = _resolve_quote_of(quoted, messages)
                    if quote_of is None:
                        note_parts.append("引用目标未匹配:「%s」" % quoted)

        if local_note:
            note_parts.append(local_note)

        inferred = not explicit
        messages.append(Message(
            mid="m%d" % (len(messages) + 1),
            sender=sender or "",
            content=content,
            timestamp=ts,
            msg_type=msg_type,
            inferred_time=inferred,
            quote_of=quote_of))

    # ---- 装配 ----
    peer = header.get("聊天对象") or ""
    me = me_nickname
    me_from_header = header.get("消息发起人")
    if me_from_header:
        me = me_from_header

    if me is None:
        if peer:
            others = [n for n in nicknames if n and n != peer]
            if others:
                me = others[0]
        else:
            if nicknames:
                me = nicknames[0]
                note_parts.append("无头字段,默认首个昵称为本机(me)")

    # sender 规范化:me / peer 昵称归一;系统消息主语等保留原文
    for m in messages:
        if m.sender == me:
            m.sender = "me"
        elif peer and m.sender == peer:
            m.sender = peer

    if not peer:
        non_me = [n for n in nicknames if n and n != me]
        if non_me:
            peer = non_me[0]
        elif nicknames:
            peer = nicknames[0]

    created_at = _parse_header_time(header.get("开始时间") or "")
    if created_at is None and messages:
        created_at = messages[0].timestamp
    if created_at is None:
        note_parts.append("文件起始时间戳缺失,采用回退时间")
    updated_at = _parse_header_time(header.get("结束时间") or "")
    if updated_at is None and messages:
        updated_at = messages[-1].timestamp

    session_id = "s" + hashlib.sha1(
        ((peer or "") + (created_at or "")).encode("utf-8")).hexdigest()[:16]

    note = None
    if note_parts:
        seen = []
        for p in note_parts:
            if p not in seen:
                seen.append(p)
        note = ";".join(seen)

    return ChatSession(
        session_id=session_id,
        peer=peer,
        created_at=created_at,
        updated_at=updated_at,
        message_count=len(messages),
        note=note,
        messages=messages)


def parse_wechat_file(path, me_nickname=None):
    """读取文件(自动剥离 BOM)并解析。"""
    with io.open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    return parse_wechat_text(text, me_nickname=me_nickname)

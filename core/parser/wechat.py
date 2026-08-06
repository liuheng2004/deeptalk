# -*- coding: utf-8 -*-
"""????????????txt ????

??:docs/guides/parser-spec.md
??:docs/contracts/session.schema.json
"""
from __future__ import absolute_import, unicode_literals

import hashlib
import io
import re

# ?????,?? ISO8601 ?
TZ_OFFSET = "+08:00"

_TIME_LINE_RE = re.compile(
    r"^(?P<date>\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?|??\s*\d{1,2}:\d{2}|??\s*\d{1,2}:\d{2})\s+"
    r"(?P<nick>.+)$"
)
_TIME_ONLY_RE = re.compile(
    r"^(?P<time>\d{1,2}:\d{2}(?::\d{2})?|??\s*\d{1,2}:\d{2}|??\s*\d{1,2}:\d{2})\s+"
    r"(?P<nick>.+)$"
)

_SYSTEM_PATTERNS = [
    re.compile(r"^(.+)\s+???????$"),
    re.compile(r"^(.{1,20})\s+???.{0,20}$"),
    re.compile(r"^?????.+???????????$"),
    re.compile(r"^.+????????.+$"),
    re.compile(r"^?????????$"),
    re.compile(r"^???.+???.+$"),
]

_EMOJI_OR_NON_TEXT_RE = re.compile(r"^\[[^\[\]]+\]$")


class Message(object):
    """????????"""

    def __init__(self, mid, sender, content, timestamp, msg_type="text",
                 inferred_time=False, quote_of=None):
        self.id = mid
        self.sender = sender
        self.content = content
        self.timestamp = timestamp  # ISO8601 ???(? +08:00)
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
    """????????,???? session.schema.json?"""

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
    """??????????;????;??????????"""
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


def _parse_header(blocks):
    """?? A:????????????(?? ':' ??????)?"""
    header = {}
    if not blocks:
        return header, blocks
    first = blocks[0]
    if not first:
        return header, blocks
    is_time = _TIME_LINE_RE.match(first[0]) or _TIME_ONLY_RE.match(first[0])
    if is_time:
        return header, blocks
    for line in first:
        if ":" in line:
            key, _, value = line.partition(":")
            header[key.strip()] = value.strip()
        elif "?" in line:
            key, _, value = line.partition("?")
            header[key.strip()] = value.strip()
    return header, blocks[1:]


def _parse_datetime(iso_text):
    """'YYYY-M-D H:MM:SS' -> (date, time) ??,???????"""
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$", iso_text)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)),
            int(m.group(4)), int(m.group(5)), int(m.group(6) or 0))


def _parse_header_time(text):
    m = re.match(
        r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T]"
        r"(\d{1,2}):(\d{2})(?::(\d{2}))?$", text.strip())
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    hh, mm, ss = int(m.group(4)), int(m.group(5)), int(m.group(6) or 0)
    return _format_iso(y, mo, d, hh, mm, ss)


def _parse_time_value(text):
    """? '9:30' / '09:30:00' / '?? 9:30' / '??1:05' ??? (h, m, s)?"""
    text = text.strip()
    period = None
    if text.startswith("??"):
        period = "am"
        text = text[2:].strip()
    elif text.startswith("??"):
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
    """?? (type, sender) ? None?"""
    for pat in _SYSTEM_PATTERNS:
        m = pat.match(line.strip())
        if m:
            if pat.groups:
                return "system", m.group(1)
            return "system", None
    return None


def _quote_match(lines):
    """????????+ ???? -> (quoted, reply) ? None?"""
    first = lines[0].strip()
    if not first.startswith("?") or "?" not in first:
        return None
    end = first.index("?")
    quoted = first[1:end].strip()
    rest = lines[1:]
    reply = "\n".join(l.rstrip() for l in rest).strip()
    if not reply:
        reply = ""
    return quoted, reply


def _normalize_text(s):
    return re.sub(r"[\s?????,.!?]+", "", s)


def _resolve_quote_of(quoted, messages):
    target = _normalize_text(quoted)
    best = None
    for m in reversed(messages):
        cand = _normalize_text(m.content)
        if cand == target or target in cand or cand in target:
            best = m.id
            break
    return best


def _voip_text(lines):
    """?? [??] + ????? (msg_type, content) ? None?"""
    first = lines[0].strip()
    if first != "[??]":
        return None
    rest = [l.rstrip() for l in lines[1:] if l.strip()]
    if not rest:
        return ("system", "[??]", "?????")
    second = rest[0]
    if second.startswith("?????"):
        return ("voip_text", second[len("?????"):].strip(), None)
    if second.startswith("????:"):
        return ("voip_text", second[len("????:"):].strip(), None)
    return ("voip_text", second.strip(), None)


def parse_wechat_text(text, me_nickname=None):
    """????????,?? ChatSession?

    me_nickname: ??,??????????(????????)?
    """
    text = _strip_bom(_normalize_newlines(text))
    blocks = _split_blocks(text.split("\n"))
    header, blocks = _parse_header(blocks)

    messages = []
    note_parts = []
    last_date = None
    last_ts = None
    last_sender = None
    nicknames = []

    for block in blocks:
        if not block:
            continue
        # ???:????
        tm = _TIME_LINE_RE.match(block[0].strip())
        explicit = False
        inherited_date = None
        if tm:
            date_str = tm.group("date")
            date_parts = re.split(r"[-/]", date_str)
            y, mo, d = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
            tv = _parse_time_value(tm.group("time"))
            nick = tm.group("nick").strip()
            if tv:
                hh, mm, ss = tv
                ts = _format_iso(y, mo, d, hh, mm, ss)
                explicit = True
                last_date = (y, mo, d)
                last_ts = ts
                last_sender = nick
                nicknames.append(nick)
                content_lines = [l.rstrip() for l in block[1:]]
            else:
                content_lines = [l.rstrip() for l in block]
        else:
            tonly = _TIME_ONLY_RE.match(block[0].strip())
            if tonly:
                tv = _parse_time_value(tonly.group("time"))
                nick = tonly.group("nick").strip()
                if tv and last_date:
                    y, mo, d = last_date
                    hh, mm, ss = tv
                    ts = _format_iso(y, mo, d, hh, mm, ss)
                    explicit = True
                    last_ts = ts
                    last_sender = nick
                    nicknames.append(nick)
                    note_parts.append("??????????,????????")
                    content_lines = [l.rstrip() for l in block[1:]]
                else:
                    content_lines = [l.rstrip() for l in block]
            else:
                content_lines = [l.rstrip() for l in block]

        if not explicit:
            # ?????:????????(??)
            ts = last_ts
            inferred = True
        else:
            ts = last_ts
            inferred = False

        # ?????????
        while content_lines and content_lines[0].strip() == "":
            content_lines.pop(0)
        while content_lines and content_lines[-1].strip() == "":
            content_lines.pop()

        if not content_lines:
            continue

        # ????:system -> voip_text -> quote -> text
        msg_type = "text"
        content = "\n".join(content_lines).strip()
        sender = last_sender
        quote_of = None
        local_note = None

        sys_hit = _system_match(content_lines[0])
        if sys_hit:
            msg_type, subj = sys_hit
            if subj:
                sender = subj
                nicknames.append(subj)
        elif msg_type == "text":
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
                        note_parts.append("???????:?%s?" % quoted)
        elif msg_type == "text" and _EMOJI_OR_NON_TEXT_RE.match(content_lines[0].strip()):
            msg_type = "system"

        if local_note:
            note_parts.append(local_note)

        if sender is None:
            sender = ""

        # sender ????????????(??????)
        mid = "m%d" % (len(messages) + 1)
        messages.append(Message(
            mid=mid, sender=sender, content=content, timestamp=ts,
            msg_type=msg_type, inferred_time=inferred,
            quote_of=quote_of))

        if not inferred and ts:
            last_ts = ts
        if ts and (last_ts is None or ts > last_ts):
            last_ts = ts

    # ---- ?? ----
    peer = header.get("????") or ""
    me = me_nickname
    me_from_header = header.get("?????")
    if me_from_header:
        me = me_from_header
    elif not me and header.get("????"):
        others = [n for n in nicknames if n and n != peer]
        if others:
            me = others[0]
    if me is None:
        candidates = [n for n in nicknames if n]
        if candidates:
            me = candidates[0]
            note_parts.append("????,?????????(me)")

    me_seen = False
    for m in messages:
        if m.sender == me:
            m.sender = "me"
            me_seen = True
        elif m.sender == peer:
            m.sender = peer
        elif m.sender and m.sender != peer:
            # ???????:????
            pass

    if not peer:
        non_me = [n for n in nicknames if n and n != me]
        if non_me:
            peer = non_me[0]
    if not peer and nicknames:
        peer = nicknames[0]

    created_at = _parse_header_time(header.get("????") or "") or (
        messages[0].timestamp if messages else None)
    updated_at = _parse_header_time(header.get("????") or "") or (
        messages[-1].timestamp if messages else None)

    if created_at is None:
        note_parts.append("?????????,??????")

    session_id = "s" + hashlib.sha1(
        (peer or "") + (created_at or "")).hexdigest()[:16]

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
        messages=messages,
    )


def parse_wechat_file(path, me_nickname=None):
    """????(???? BOM)????"""
    with io.open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    return parse_wechat_text(text, me_nickname=me_nickname)

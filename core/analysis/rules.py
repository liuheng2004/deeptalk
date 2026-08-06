# -*- coding: utf-8 -*-
"""
规则初筛引擎(本地,无 API 调用)。
四维: emotion / event / continuity / interaction
"""

from __future__ import absolute_import

from typing import Any, Dict, List, Tuple


# ── 关键词库 ──

EMOTION_SELF_DISCLOSURE = [
    "其实我", "说实话", "老实说", "说真的", "不瞒你说",
    "我一直觉得", "我内心里", "我心里", "我觉得自己",
    "我从来没有", "从来没告诉过别人", "我有个秘密",
    "说出来你可能不信", "你知道吗", "我其实",
]

EMOTION_VULNERABILITY = [
    "难过", "伤心", "想哭", "哭了", "崩溃",
    "压力", "好累", "撑不住", "受不了", "顶不住",
    "焦虑", "害怕", "担心", "紧张", "不安",
    "迷茫", "不知道怎么办", "没方向", "困惑",
    "孤独", "寂寞", "无助", "绝望",
    "失恋", "分手", "被甩", "离了",
    "失眠", "睡不着", "做噩梦",
]

EMOTION_DEEP_SHARING = [
    "真心话", "掏心掏肺", "说句心里话",
    "我觉得人生", "活着", "意义",
    "为什么总是", "凭什么",
    "原生家庭", "童年", "从小",
    "自卑", "不配", "不够好",
]

EVENT_CONFESSION = [
    "我喜欢你", "我爱你", "在一起", "恋爱",
    "表白", "告白", "心动", "暗恋",
    "你有喜欢的人吗", "我们在一起吧",
]

EVENT_APOLOGY = [
    "对不起", "抱歉", "我的错", "是我不好",
    "原谅我", "请原谅", "别生气", "我错了",
    "不该", "不应该", "后悔",
]

EVENT_RECONCILIATION = [
    "和好", "和好了", "和好吧", "不吵了",
    "过去的事就过去了", "重新开始",
    "还做朋友", "以后好好的",
]

EVENT_FAREWELL = [
    "再见", "告别", "保重", "照顾好自己",
    "最后一次", "后会无期", "珍重",
    "离开", "要走", "搬走", "出国",
]

EVENT_MAJOR_DECISION = [
    "辞职", "裸辞", "跳槽", "offer",
    "面试", "考研", "考公", "出国留学",
    "搬家", "买房", "结婚", "生小孩", "要孩子",
    "离婚", "分手吧", "决定了", "我选择",
    "我想好了", "就这么定了",
]

INTERACTION_EMPATHY = [
    "我理解", "我明白", "我懂", "我懂得",
    "我能感觉到", "我知道你", "我知道这种",
    "你辛苦了", "不容易", "委屈了",
    "抱抱", "没事的", "会好的", "我陪你",
    "慢慢来", "不急", "别急",
]

INTERACTION_ENGAGEMENT = [
    "然后呢", "后来呢", "为什么", "怎么说", "具体呢",
    "你觉得呢", "你感觉", "你怎么想", "你打算",
]

INTERACTION_ACTIVE_LISTENING = [
    "嗯嗯", "对对", "说到", "是的",
    "确实", "没错", "这样啊", "原来如此",
]


# ── 辅助函数 ──

def _match_score(text, keywords):
    """基于关键词命中数计算 0-100 的匹配分。"""
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    if hits == 0:
        return 0.0
    # 递增: 1=65, 2=78, 3=87, 4=93, 5+=97
    if hits >= 5:
        return 97.0
    score_map = {1: 65.0, 2: 78.0, 3: 87.0, 4: 93.0}
    return score_map.get(hits, 97.0)


def _count_keyword_hits(text, keywords):
    text_lower = text.lower()
    return sum(text_lower.count(kw.lower()) for kw in keywords)


def _avg_message_length(messages):
    if not messages:
        return 0.0
    return sum(len(m.get("content", "")) for m in messages) / float(len(messages))


def _turn_alternation_ratio(messages):
    if len(messages) < 2:
        return 0.0
    switches = sum(1 for i in range(1, len(messages))
                   if messages[i].get("sender") != messages[i - 1].get("sender"))
    return switches / float(len(messages) - 1)


def _parse_iso_timestamp(ts_str):
    """Python 3.5 兼容的 ISO 时间戳解析。"""
    from datetime import datetime
    ts_str = ts_str.strip() if ts_str else ""
    if not ts_str:
        return None
    if "+" in ts_str:
        ts_str = ts_str.split("+")[0]
    elif ts_str.endswith("Z"):
        ts_str = ts_str[:-1]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(ts_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _time_concentration_hours(messages):
    if len(messages) < 2:
        return 0.0
    try:
        t0 = _parse_iso_timestamp(messages[0].get("timestamp", ""))
        t1 = _parse_iso_timestamp(messages[-1].get("timestamp", ""))
        if t0 is None or t1 is None:
            return 0.0
        return abs((t1 - t0).total_seconds()) / 3600.0
    except (ValueError, TypeError, AttributeError):
        return 0.0


def _question_count(text):
    return text.count("?") + text.count("吗") + text.count("呢") + text.count("吧")


# ── 数据类 ──

class RuleScores(object):
    def __init__(self, emotion=0.0, event=0.0, continuity=0.0, interaction=0.0,
                 confidence=0.0, hints=None):
        self.emotion = emotion
        self.event = event
        self.continuity = continuity
        self.interaction = interaction
        self.confidence = confidence
        self.hints = hints or []

    def __repr__(self):
        return "RuleScores(emotion={:.1f}, event={:.1f}, continuity={:.1f}, interaction={:.1f})".format(
            self.emotion, self.event, self.continuity, self.interaction)


# ── 维度评分 ──

def score_emotion(messages):
    all_text = "\n".join(m.get("content", "") for m in messages)
    hints = []
    s_disclosure = _match_score(all_text, EMOTION_SELF_DISCLOSURE)
    s_vulnerability = _match_score(all_text, EMOTION_VULNERABILITY)
    s_deep = _match_score(all_text, EMOTION_DEEP_SHARING)
    base_score = s_disclosure * 0.35 + s_vulnerability * 0.40 + s_deep * 0.25
    avg_len = _avg_message_length(messages)
    length_bonus = min(avg_len / 200.0, 0.15) * 100.0
    final = min(base_score + length_bonus, 100.0)
    if s_disclosure > 30:
        hints.append("自我暴露(+{:.0f})".format(s_disclosure))
    if s_vulnerability > 30:
        hints.append("情绪表达(+{:.0f})".format(s_vulnerability))
    if s_deep > 30:
        hints.append("深度分享(+{:.0f})".format(s_deep))
    return final, hints


def score_event(messages):
    """评估关键节点维度。

    使用各事件类别的最高分(max)而非加权和:
    告白/道歉/和解/离别/重大决定任一类命中即为关键事件。
    """
    all_text = "\n".join(m.get("content", "") for m in messages)
    hints = []
    subs = {"告白": EVENT_CONFESSION, "道歉": EVENT_APOLOGY,
            "和解": EVENT_RECONCILIATION, "离别": EVENT_FAREWELL,
            "重大决定": EVENT_MAJOR_DECISION}
    # 取各类别最高分,再加成(20% bonus for additional categories hit)
    category_scores = {}
    for label, kws in subs.items():
        sub_score = _match_score(all_text, kws)
        category_scores[label] = sub_score
        if sub_score > 30:
            hints.append("{}(+{:.0f})".format(label, sub_score))
    # 最高分 + 额外类别加成
    scores_sorted = sorted(category_scores.values(), reverse=True)
    best = scores_sorted[0] if scores_sorted else 0.0
    # 每个额外命中类别 +10 分
    extra = sum(10.0 for s in scores_sorted[1:] if s > 0)
    return min(best + extra, 100.0), hints


def score_continuity(messages):
    """评估主题连续性维度。

    考察消息数、轮替比例、时间密度,并考虑平均内容长度。
    短消息的事务性对话不应得高分。
    """
    hints = []
    n = len(messages)
    if n < 2:
        return 0.0, ["消息数不足"]

    avg_len = _avg_message_length(messages)

    # 消息数量分:10+ 条算高连续性,但受内容长度制约
    count_score = min(n / 15.0, 1.0) * 60.0

    # 内容长度修正:平均消息 < 10 字符说明是事务性对话,大幅降分
    if avg_len < 10:
        content_factor = 0.3
    elif avg_len < 20:
        content_factor = 0.5
    elif avg_len < 40:
        content_factor = 0.7
    else:
        content_factor = 1.0
    count_score *= content_factor

    # 轮替比例:接近 1.0 说明对话活跃,但短消息轮替价值低
    ratio = _turn_alternation_ratio(messages)
    ratio_score = ratio * 25.0 * content_factor

    # 时间密度:越集中分越高;跨天大幅降分
    hours = _time_concentration_hours(messages)
    if hours <= 1:
        density_score = 15.0
    elif hours <= 3:
        density_score = 10.0
    elif hours <= 12:
        density_score = 5.0
    else:
        density_score = 0.0

    total = count_score + ratio_score + density_score

    if count_score > 20:
        hints.append("多轮对话({}条)".format(n))
    if ratio > 0.5:
        hints.append("活跃交替({:.0%})".format(ratio))
    if hours <= 3 and hours > 0:
        hints.append("时间集中({:.1f}h)".format(hours))

    return min(total, 100.0), hints


def score_interaction(messages):
    hints = []
    all_text = "\n".join(m.get("content", "") for m in messages)
    empathy_score = _match_score(all_text, INTERACTION_EMPATHY)
    engagement_hits = _count_keyword_hits(all_text, INTERACTION_ENGAGEMENT)
    engagement_score = min(engagement_hits * 15, 30)
    listen_hits = _count_keyword_hits(all_text, INTERACTION_ACTIVE_LISTENING)
    listen_score = min(listen_hits * 5, 20)
    question_score = min(_question_count(all_text) * 5, 20)
    total = empathy_score + engagement_score + listen_score + question_score
    if empathy_score > 20:
        hints.append("共情回应(+{:.0f})".format(empathy_score))
    if engagement_score > 10:
        hints.append("深度追问(+{:.0f})".format(engagement_score))
    if question_score > 5:
        hints.append("问句互动(+{:.0f})".format(question_score))
    return min(total, 100.0), hints


# ── 综合评分 ──

DIMENSION_WEIGHTS = {"emotion": 0.35, "event": 0.25, "continuity": 0.20, "interaction": 0.20}


def compute_rule_scores(messages):
    emotion, e_hints = score_emotion(messages)
    event, ev_hints = score_event(messages)
    continuity, c_hints = score_continuity(messages)
    interaction, i_hints = score_interaction(messages)
    all_hints = e_hints + ev_hints + c_hints + i_hints
    hint_count = len(all_hints)
    if hint_count >= 6:
        confidence = 0.90
    elif hint_count >= 4:
        confidence = 0.75
    elif hint_count >= 2:
        confidence = 0.50
    else:
        confidence = 0.25
    return RuleScores(emotion=round(emotion, 1), event=round(event, 1),
                      continuity=round(continuity, 1), interaction=round(interaction, 1),
                      confidence=round(confidence, 2), hints=all_hints)


def compute_depth_score(scores):
    return round(
        scores.emotion * DIMENSION_WEIGHTS["emotion"]
        + scores.event * DIMENSION_WEIGHTS["event"]
        + scores.continuity * DIMENSION_WEIGHTS["continuity"]
        + scores.interaction * DIMENSION_WEIGHTS["interaction"], 1)


def should_call_api(scores, depth, cfg=None):
    from .config import config as default_cfg
    cfg = cfg or default_cfg
    if depth < cfg.rule_low_conf_cap:
        return False, "rule score {:.0f} below low cap {:.0f}".format(depth, cfg.rule_low_conf_cap)
    if depth >= cfg.rule_high_conf_cap:
        return False, "rule score {:.0f} above high cap {:.0f}".format(depth, cfg.rule_high_conf_cap)
    return True, "rule score {:.0f} in fallback range".format(depth)

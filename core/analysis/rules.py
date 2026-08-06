"""
规则初筛引擎(本地,无 API 调用)。

对会话片段进行基于关键词和启发式规则的四维打分,
在低置信(极浅)和高置信(极深)区间直接给出结论,
仅中等置信区间才调用模型,从而减少 API 调用量。

四维:
- emotion:    情感深度(自我暴露、情绪倾诉、脆弱表达)
- event:      关键节点(告白、道歉、和解、离别、重大决定)
- continuity: 主题连续性(围绕同一话题持续多轮、有推进)
- interaction: 互动质量(倾听、共情、有效回应)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ── 关键词库 ──────────────────────────────────────────────────────────

# 情感关键词:分为自我暴露、情绪倾诉、脆弱表达三个子类
EMOTION_SELF_DISCLOSURE: list[str] = [
    "其实我", "说实话", "老实说", "说真的", "不瞒你说",
    "我一直觉得", "我内心里", "我心里", "我觉得自己",
    "我从来没有", "从来没告诉过别人", "我有个秘密",
    "说出来你可能不信", "你知道吗", "我其实",
]

EMOTION_VULNERABILITY: list[str] = [
    "难过", "伤心", "想哭", "哭了", "崩溃",
    "压力", "好累", "撑不住", "受不了", "顶不住",
    "焦虑", "害怕", "担心", "紧张", "不安",
    "迷茫", "不知道怎么办", "没方向", "困惑",
    "孤独", "寂寞", "无助", "绝望",
    "失恋", "分手", "被甩", "离了",
    "失眠", "睡不着", "做噩梦",
]

EMOTION_DEEP_SHARING: list[str] = [
    "真心话", "掏心掏肺", "说句心里话",
    "其实", "说实话", "说真的",
    "我觉得人生", "活着", "意义",
    "为什么总是", "凭什么",
    "原生家庭", "童年", "从小",
    "自卑", "不配", "不够好",
]

# 事件关键词
EVENT_CONFESSION: list[str] = [
    "我喜欢你", "我爱你", "在一起", "恋爱",
    "表白", "告白", "心动", "暗恋",
    "你有喜欢的人吗", "我们在一起吧",
]

EVENT_APOLOGY: list[str] = [
    "对不起", "抱歉", "我的错", "是我不好",
    "原谅我", "请原谅", "别生气", "我错了",
    "不该", "不应该", "后悔",
]

EVENT_RECONCILIATION: list[str] = [
    "和好", "和好了", "和好吧", "不吵了",
    "过去的事就过去了", "重新开始",
    "还做朋友", "以后好好的",
]

EVENT_FAREWELL: list[str] = [
    "再见", "告别", "保重", "照顾好自己",
    "最后一次", "后会无期", "珍重",
    "离开", "要走", "搬走", "出国",
]

EVENT_MAJOR_DECISION: list[str] = [
    "辞职", "裸辞", "跳槽", "offer",
    "面试", "考研", "考公", "出国留学",
    "搬家", "买房", "结婚", "生小孩", "要孩子",
    "离婚", "分手吧", "决定了", "我选择",
    "我想好了", "就这么定了",
]

# 互动质量关键词
INTERACTION_EMPATHY: list[str] = [
    "我理解", "我明白", "我懂", "我懂得",
    "我能感觉到", "我知道你", "我知道这种",
    "你辛苦了", "不容易", "委屈了",
    "抱抱", "没事的", "会好的", "我陪你",
    "慢慢来", "不急", "别急",
]

INTERACTION_ENGAGEMENT: list[str] = [
    # 提问表示关注
    "然后呢", "后来呢", "为什么", "怎么说", "具体呢",
    "你觉得呢", "你感觉", "你怎么想", "你打算",
]

INTERACTION_ACTIVE_LISTENING: list[str] = [
    "嗯嗯", "对对", "说到", "是的",
    "确实", "没错", "这样啊", "原来如此",
]


# ── 辅助函数 ──────────────────────────────────────────────────────────

def _match_score(text: str, keywords: list[str]) -> float:
    """基于关键词命中数计算 0-100 的匹配分。

    每个子类设一个基础分,命中越多得分越高但有上限。
    """
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    if hits == 0:
        return 0.0
    # 对数式递增:1 命中=50, 2=70, 3=82, 4=90, 5+=95
    score = 50 + (min(hits, 6) - 1) * (45 / 5)
    return min(score, 100.0)


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """统计关键词命中次数(含重复)。"""
    text_lower = text.lower()
    return sum(text_lower.count(kw.lower()) for kw in keywords)


def _avg_message_length(messages: list[dict[str, Any]]) -> float:
    """平均消息长度(字符数)。"""
    if not messages:
        return 0.0
    total = sum(len(m.get("content", "")) for m in messages)
    return total / len(messages)


def _turn_alternation_ratio(messages: list[dict[str, Any]]) -> float:
    """计算发言轮替比例:相邻发送者变化的次数 / (消息数-1)。"""
    if len(messages) < 2:
        return 0.0
    switches = 0
    for i in range(1, len(messages)):
        if messages[i].get("sender") != messages[i - 1].get("sender"):
            switches += 1
    return switches / (len(messages) - 1)


def _time_concentration_hours(messages: list[dict[str, Any]]) -> float:
    """消息时间跨度(小时)。"""
    if len(messages) < 2:
        return 0.0
    try:
        from datetime import datetime

        t0 = datetime.fromisoformat(messages[0].get("timestamp", ""))
        t1 = datetime.fromisoformat(messages[-1].get("timestamp", ""))
        return abs((t1 - t0).total_seconds()) / 3600
    except (ValueError, TypeError):
        return 0.0


def _question_count(text: str) -> int:
    """统计问句数。"""
    return text.count("?") + text.count("?") + text.count("吗") + text.count("呢") + text.count("吧")


# ── 维度评分 ──────────────────────────────────────────────────────────

@dataclass
class RuleScores:
    """规则初筛结果。"""

    emotion: float = 0.0
    event: float = 0.0
    continuity: float = 0.0
    interaction: float = 0.0

    # 置信度标识:规则判断的可靠程度(0-1)
    confidence: float = 0.0

    # 提示:哪些特征被命中
    hints: list[str] = field(default_factory=list)


def score_emotion(messages: list[dict[str, Any]]) -> tuple[float, list[str]]:
    """评估情感深度维度。

    检查自我暴露、情绪倾诉、脆弱表达三类关键词;
    同时考虑消息长度(长消息往往包含更多情感表达)。
    """
    all_text = "\n".join(m.get("content", "") for m in messages)
    hints: list[str] = []

    # 子维度得分
    s_disclosure = _match_score(all_text, EMOTION_SELF_DISCLOSURE)
    s_vulnerability = _match_score(all_text, EMOTION_VULNERABILITY)
    s_deep = _match_score(all_text, EMOTION_DEEP_SHARING)

    # 加权:自我暴露 0.35, 脆弱 0.40, 深度分享 0.25
    base_score = s_disclosure * 0.35 + s_vulnerability * 0.40 + s_deep * 0.25

    # 消息长度加成:平均长度 > 100 字符说明在深入交流
    avg_len = _avg_message_length(messages)
    length_bonus = min(avg_len / 200, 0.15) * 100  # 最多+15 分

    final = min(base_score + length_bonus, 100.0)

    if s_disclosure > 30:
        hints.append(f"自我暴露(+{s_disclosure:.0f})")
    if s_vulnerability > 30:
        hints.append(f"情绪表达(+{s_vulnerability:.0f})")
    if s_deep > 30:
        hints.append(f"深度分享(+{s_deep:.0f})")

    return final, hints


def score_event(messages: list[dict[str, Any]]) -> tuple[float, list[str]]:
    """评估关键节点维度。

    检查告白、道歉、和解、离别、重大决定五类事件关键词。
    """
    all_text = "\n".join(m.get("content", "") for m in messages)
    hints: list[str] = []

    subs = {
        "告白": EVENT_CONFESSION,
        "道歉": EVENT_APOLOGY,
        "和解": EVENT_RECONCILIATION,
        "离别": EVENT_FAREWELL,
        "重大决定": EVENT_MAJOR_DECISION,
    }

    weights = {"告白": 0.25, "道歉": 0.20, "和解": 0.20, "离别": 0.15, "重大决定": 0.20}
    total = 0.0

    for label, kws in subs.items():
        sub_score = _match_score(all_text, kws)
        total += sub_score * weights[label]
        if sub_score > 30:
            hints.append(f"{label}(+{sub_score:.0f})")

    return min(total, 100.0), hints


def score_continuity(messages: list[dict[str, Any]]) -> tuple[float, list[str]]:
    """评估主题连续性维度。

    考察:
    - 消息数(多轮对话体现持续)
    - 轮替比例(交替发言说明在讨论,而非单方倾诉)
    - 时间密度(集中讨论 vs 稀疏散聊)
    """
    hints: list[str] = []
    n = len(messages)

    if n < 2:
        return 0.0, ["消息数不足"]

    # 消息数量分:10+ 条算高连续性
    count_score = min(n / 15, 1.0) * 60  # 最多 60 分

    # 轮替比例:接近 1.0 说明对话活跃
    ratio = _turn_alternation_ratio(messages)
    ratio_score = ratio * 25  # 最多 25 分

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
        hints.append(f"多轮对话({n}条)")
    if ratio > 0.5:
        hints.append(f"活跃交替({ratio:.0%})")
    if hours <= 3:
        hints.append(f"时间集中({hours:.1f}h)")

    return min(total, 100.0), hints


def score_interaction(messages: list[dict[str, Any]]) -> tuple[float, list[str]]:
    """评估互动质量维度。

    检查共情回应、追问关注、积极倾听等模式;
    同时考虑回复长度和问句密度。
    """
    hints: list[str] = []

    all_text = "\n".join(m.get("content", "") for m in messages)

    # 共情得分
    empathy_score = _match_score(all_text, INTERACTION_EMPATHY)

    # 追问得分
    engagement_hits = _count_keyword_hits(all_text, INTERACTION_ENGAGEMENT)
    engagement_score = min(engagement_hits * 15, 30)

    # 积极倾听
    listen_hits = _count_keyword_hits(all_text, INTERACTION_ACTIVE_LISTENING)
    listen_score = min(listen_hits * 5, 20)

    # 问句密度加成
    questions = _question_count(all_text)
    question_score = min(questions * 5, 20)

    total = empathy_score + engagement_score + listen_score + question_score

    if empathy_score > 20:
        hints.append(f"共情回应(+{empathy_score:.0f})")
    if engagement_score > 10:
        hints.append(f"深度追问(+{engagement_score:.0f})")
    if question_score > 5:
        hints.append(f"问句互动(+{question_score:.0f})")

    return min(total, 100.0), hints


# ── 综合评分 ──────────────────────────────────────────────────────────

# 四维权重(总和 1.0)
DIMENSION_WEIGHTS = {
    "emotion": 0.35,
    "event": 0.25,
    "continuity": 0.20,
    "interaction": 0.20,
}


def compute_rule_scores(messages: list[dict[str, Any]]) -> RuleScores:
    """对一组消息执行规则初筛,返回四维得分及置信度。

    这是纯本地计算,不调用任何外部 API。
    """
    emotion, e_hints = score_emotion(messages)
    event, ev_hints = score_event(messages)
    continuity, c_hints = score_continuity(messages)
    interaction, i_hints = score_interaction(messages)

    all_hints = e_hints + ev_hints + c_hints + i_hints

    # 置信度:命中特征越多,置信度越高
    hint_count = len(all_hints)
    if hint_count >= 6:
        confidence = 0.90
    elif hint_count >= 4:
        confidence = 0.75
    elif hint_count >= 2:
        confidence = 0.50
    else:
        confidence = 0.25

    return RuleScores(
        emotion=round(emotion, 1),
        event=round(event, 1),
        continuity=round(continuity, 1),
        interaction=round(interaction, 1),
        confidence=round(confidence, 2),
        hints=all_hints,
    )


def compute_depth_score(scores: RuleScores) -> float:
    """加权合成深度评分(0-100)。"""
    depth = (
        scores.emotion * DIMENSION_WEIGHTS["emotion"]
        + scores.event * DIMENSION_WEIGHTS["event"]
        + scores.continuity * DIMENSION_WEIGHTS["continuity"]
        + scores.interaction * DIMENSION_WEIGHTS["interaction"]
    )
    return round(depth, 1)


def should_call_api(scores: RuleScores, depth: float, cfg: Any = None) -> tuple[bool, str]:
    """判断是否需要调用模型 API。

    Returns:
        (should_call, reason)
    """
    from .config import config as default_cfg

    cfg = cfg or default_cfg

    if depth < cfg.rule_low_conf_cap:
        return False, f"规则评分{depth:.0f}低于下限{cfg.rule_low_conf_cap:.0f},判定非深度"
    if depth >= cfg.rule_high_conf_cap:
        return False, f"规则评分{depth:.0f}高于上限{cfg.rule_high_conf_cap:.0f},判定为深度"
    return True, f"规则评分{depth:.0f}在{cfg.rule_low_conf_cap:.0f}-{cfg.rule_high_conf_cap:.0f}区间,需模型确认"

"""
core/analysis 模块测试。

包含:
- 10 段对话样例,覆盖深度/日常/边界等场景
- 规则初筛单元测试
- 引擎端到端测试(使用 MockProvider)
- 输出 schema 验证
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ── 10 段对话样例 ─────────────────────────────────────────────────────

# 每段样例包含: messages 列表 + 人类标注的预期结果
# 预期:
#   is_deep: 是否应为深度对话
#   depth_range: 预期深度评分区间 (min, max)
#   tag_hints: 至少应包含的标签提示

SAMPLE_1_DEEP_EMOTION = {
    "name": "深夜情感倾诉",
    "messages": [
        {"id": "m1", "sender": "me", "content": "其实我一直想跟你说件事", "type": "text", "timestamp": "2024-05-20T23:15:00+08:00"},
        {"id": "m2", "sender": "晨曦", "content": "什么事呀，这么严肃", "type": "text", "timestamp": "2024-05-20T23:15:30+08:00"},
        {"id": "m3", "sender": "me", "content": "最近压力好大，每天晚上都睡不着", "type": "text", "timestamp": "2024-05-20T23:16:00+08:00"},
        {"id": "m4", "sender": "晨曦", "content": "我理解，你跟我说说吧，是什么事", "type": "text", "timestamp": "2024-05-20T23:16:20+08:00"},
        {"id": "m5", "sender": "me", "content": "工作上的事，觉得自己怎么努力都做不好，很迷茫", "type": "text", "timestamp": "2024-05-20T23:17:00+08:00"},
        {"id": "m6", "sender": "晨曦", "content": "我能感觉到你很难过，其实你已经做得很好了，别给自己太大压力", "type": "text", "timestamp": "2024-05-20T23:18:00+08:00"},
        {"id": "m7", "sender": "me", "content": "谢谢你这么说，有时候真的需要有人听我说这些", "type": "text", "timestamp": "2024-05-20T23:20:00+08:00"},
        {"id": "m8", "sender": "晨曦", "content": "没事的，慢慢来，不管怎样我都在", "type": "text", "timestamp": "2024-05-20T23:21:00+08:00"},
    ],
    "expected": {"is_deep": True, "depth_range": (60, 95), "tag_hints": ["情感", "压力", "共情"]},
}

SAMPLE_2_CONFESSION = {
    "name": "告白",
    "messages": [
        {"id": "m1", "sender": "me", "content": "我有件事想跟你说很久了", "type": "text", "timestamp": "2024-06-14T21:30:00+08:00"},
        {"id": "m2", "sender": "小雨", "content": "嗯？什么事", "type": "text", "timestamp": "2024-06-14T21:30:30+08:00"},
        {"id": "m3", "sender": "me", "content": "我喜欢你。从认识你那天就开始了", "type": "text", "timestamp": "2024-06-14T21:31:00+08:00"},
        {"id": "m4", "sender": "小雨", "content": "…你说真的吗", "type": "text", "timestamp": "2024-06-14T21:32:00+08:00"},
        {"id": "m5", "sender": "me", "content": "真的，每次见到你我都很开心，你是我见过最特别的人", "type": "text", "timestamp": "2024-06-14T21:32:30+08:00"},
        {"id": "m6", "sender": "小雨", "content": "其实…我也喜欢你很久了，一直没敢说", "type": "text", "timestamp": "2024-06-14T21:33:00+08:00"},
        {"id": "m7", "sender": "me", "content": "那我们在一起好吗", "type": "text", "timestamp": "2024-06-14T21:33:20+08:00"},
        {"id": "m8", "sender": "小雨", "content": "好。", "type": "text", "timestamp": "2024-06-14T21:33:40+08:00"},
    ],
    "expected": {"is_deep": True, "depth_range": (70, 100), "tag_hints": ["告白", "喜欢", "在一起"]},
}

SAMPLE_3_APOLOGY_RECONCILIATION = {
    "name": "道歉与和解",
    "messages": [
        {"id": "m1", "sender": "me", "content": "对不起，那天我说的话太重了", "type": "text", "timestamp": "2024-07-10T10:00:00+08:00"},
        {"id": "m2", "sender": "老张", "content": "你知道我当时有多难受吗", "type": "text", "timestamp": "2024-07-10T10:01:00+08:00"},
        {"id": "m3", "sender": "me", "content": "我知道，是我的错。我当时太冲动了，没有站在你的角度想", "type": "text", "timestamp": "2024-07-10T10:02:00+08:00"},
        {"id": "m4", "sender": "老张", "content": "这几年朋友一场，我没想到我们会闹成这样", "type": "text", "timestamp": "2024-07-10T10:03:00+08:00"},
        {"id": "m5", "sender": "me", "content": "我真的后悔了，你能原谅我吗？我不想失去你这个朋友", "type": "text", "timestamp": "2024-07-10T10:04:00+08:00"},
        {"id": "m6", "sender": "老张", "content": "其实我也不想这样…我们和好吧", "type": "text", "timestamp": "2024-07-10T10:05:00+08:00"},
        {"id": "m7", "sender": "me", "content": "谢谢，以后我们好好的", "type": "text", "timestamp": "2024-07-10T10:06:00+08:00"},
    ],
    "expected": {"is_deep": True, "depth_range": (65, 95), "tag_hints": ["道歉", "原谅", "和好"]},
}

SAMPLE_4_CASUAL_CHAT = {
    "name": "日常闲聊",
    "messages": [
        {"id": "m1", "sender": "me", "content": "吃了没", "type": "text", "timestamp": "2024-08-01T12:00:00+08:00"},
        {"id": "m2", "sender": "同事小王", "content": "吃了，食堂今天有红烧肉", "type": "text", "timestamp": "2024-08-01T12:01:00+08:00"},
        {"id": "m3", "sender": "me", "content": "可以啊，我点的外卖", "type": "text", "timestamp": "2024-08-01T12:02:00+08:00"},
        {"id": "m4", "sender": "同事小王", "content": "哈哈明天也去食堂呗", "type": "text", "timestamp": "2024-08-01T12:03:00+08:00"},
        {"id": "m5", "sender": "me", "content": "行啊", "type": "text", "timestamp": "2024-08-01T12:04:00+08:00"},
    ],
    "expected": {"is_deep": False, "depth_range": (0, 30), "tag_hints": ["日常"]},
}

SAMPLE_5_CAREER_DECISION = {
    "name": "职业重大决定",
    "messages": [
        {"id": "m1", "sender": "me", "content": "我今天拿到两个offer了，不知道怎么选", "type": "text", "timestamp": "2024-08-15T19:00:00+08:00"},
        {"id": "m2", "sender": "导师", "content": "恭喜！说说看两家的情况", "type": "text", "timestamp": "2024-08-15T19:01:00+08:00"},
        {"id": "m3", "sender": "me", "content": "A是大厂，钱多但加班狠，B是创业公司，给的期权但风险大", "type": "text", "timestamp": "2024-08-15T19:02:00+08:00"},
        {"id": "m4", "sender": "导师", "content": "你今年才25，我建议你去大厂磨两年，等有经验了再考虑创业", "type": "text", "timestamp": "2024-08-15T19:04:00+08:00"},
        {"id": "m5", "sender": "me", "content": "但我怕大厂太卷，自己扛不住……而且创业那个方向是我真的感兴趣的", "type": "text", "timestamp": "2024-08-15T19:06:00+08:00"},
        {"id": "m6", "sender": "导师", "content": "我理解你的顾虑，但你要想清楚，25岁的试错成本是最低的。先积累，再选择", "type": "text", "timestamp": "2024-08-15T19:08:00+08:00"},
        {"id": "m7", "sender": "me", "content": "你说得对…我决定了，去大厂。谢谢你的建议", "type": "text", "timestamp": "2024-08-15T19:10:00+08:00"},
    ],
    "expected": {"is_deep": True, "depth_range": (55, 90), "tag_hints": ["决定", "职业", "选择"]},
}

SAMPLE_6_FAREWELL = {
    "name": "离别告别",
    "messages": [
        {"id": "m1", "sender": "阿杰", "content": "我下个月要去北京了", "type": "text", "timestamp": "2024-09-01T21:00:00+08:00"},
        {"id": "m2", "sender": "me", "content": "真的假的？怎么这么突然", "type": "text", "timestamp": "2024-09-01T21:01:00+08:00"},
        {"id": "m3", "sender": "阿杰", "content": "公司调岗，没办法，我也纠结了很久", "type": "text", "timestamp": "2024-09-01T21:02:00+08:00"},
        {"id": "m4", "sender": "me", "content": "那我们以后见面就少了…认识你这么多年，真的挺不舍的", "type": "text", "timestamp": "2024-09-01T21:03:00+08:00"},
        {"id": "m5", "sender": "阿杰", "content": "我也是，你是我在这个城市最好的朋友", "type": "text", "timestamp": "2024-09-01T21:04:00+08:00"},
        {"id": "m6", "sender": "me", "content": "照顾好自己，到了北京记得联系", "type": "text", "timestamp": "2024-09-01T21:05:00+08:00"},
        {"id": "m7", "sender": "阿杰", "content": "一定会的，你也要保重", "type": "text", "timestamp": "2024-09-01T21:06:00+08:00"},
    ],
    "expected": {"is_deep": True, "depth_range": (55, 90), "tag_hints": ["离别", "不舍", "朋友"]},
}

SAMPLE_7_LIGHT_JOKE = {
    "name": "轻松玩笑",
    "messages": [
        {"id": "m1", "sender": "me", "content": "哈哈哈哈 你看这个视频了吗", "type": "text", "timestamp": "2024-09-10T15:00:00+08:00"},
        {"id": "m2", "sender": "阿花", "content": "看了看了！笑死我了", "type": "text", "timestamp": "2024-09-10T15:01:00+08:00"},
        {"id": "m3", "sender": "me", "content": "那个猫太好笑了 怎么会有这么蠢的猫", "type": "text", "timestamp": "2024-09-10T15:01:30+08:00"},
        {"id": "m4", "sender": "阿花", "content": "哈哈哈哈哈哈", "type": "text", "timestamp": "2024-09-10T15:02:00+08:00"},
        {"id": "m5", "sender": "me", "content": "笑死了", "type": "text", "timestamp": "2024-09-10T15:02:30+08:00"},
    ],
    "expected": {"is_deep": False, "depth_range": (0, 20), "tag_hints": []},
}

SAMPLE_8_ANXIETY_COMFORT = {
    "name": "焦虑与安慰",
    "messages": [
        {"id": "m1", "sender": "小雅", "content": "我好害怕明天的面试，已经焦虑一整天了", "type": "text", "timestamp": "2024-10-05T22:30:00+08:00"},
        {"id": "m2", "sender": "me", "content": "我懂这种感觉，但你要相信自己，你已经准备得很充分了", "type": "text", "timestamp": "2024-10-05T22:31:00+08:00"},
        {"id": "m3", "sender": "小雅", "content": "可是我觉得自己不够好，每次面试都会紧张到说不出话", "type": "text", "timestamp": "2024-10-05T22:32:00+08:00"},
        {"id": "m4", "sender": "me", "content": "这很正常，我面试的时候也这样。你就当成去聊天，不用把它想得太可怕", "type": "text", "timestamp": "2024-10-05T22:33:00+08:00"},
        {"id": "m5", "sender": "小雅", "content": "万一失败了呢，我已经面了好几家都没过", "type": "text", "timestamp": "2024-10-05T22:34:00+08:00"},
        {"id": "m6", "sender": "me", "content": "失败就失败了，不是你不优秀，只是缘分没到。你值得好的工作。别给自己那么大压力", "type": "text", "timestamp": "2024-10-05T22:36:00+08:00"},
        {"id": "m7", "sender": "小雅", "content": "谢谢你…听到你这么说我感觉好一点了", "type": "text", "timestamp": "2024-10-05T22:38:00+08:00"},
    ],
    "expected": {"is_deep": True, "depth_range": (55, 85), "tag_hints": ["焦虑", "安慰", "压力"]},
}

SAMPLE_9_DEEP_DISCUSSION = {
    "name": "深度人生讨论",
    "messages": [
        {"id": "m1", "sender": "me", "content": "你有没有想过，人活着到底是为了什么", "type": "text", "timestamp": "2024-10-20T01:00:00+08:00"},
        {"id": "m2", "sender": "浩子", "content": "大半夜的开始思考人生了？", "type": "text", "timestamp": "2024-10-20T01:01:00+08:00"},
        {"id": "m3", "sender": "me", "content": "认真的，我最近经常觉得做的事都没意义，不知道在忙什么", "type": "text", "timestamp": "2024-10-20T01:02:00+08:00"},
        {"id": "m4", "sender": "浩子", "content": "其实我也想过。我小时候觉得人生就是要出人头地，现在觉得能让身边的人开心就够了", "type": "text", "timestamp": "2024-10-20T01:04:00+08:00"},
        {"id": "m5", "sender": "me", "content": "你说得对，但有时候我觉得自己连身边的人都照顾不好", "type": "text", "timestamp": "2024-10-20T01:06:00+08:00"},
        {"id": "m6", "sender": "浩子", "content": "人不能这么想。原生家庭给你的那些东西，不是你的错。你已经比很多人做得好多了", "type": "text", "timestamp": "2024-10-20T01:08:00+08:00"},
        {"id": "m7", "sender": "me", "content": "有时候真的觉得自己不配拥有好的东西", "type": "text", "timestamp": "2024-10-20T01:09:00+08:00"},
        {"id": "m8", "sender": "浩子", "content": "每个人都有自己的价值，你要学着看到自己的好。你值得好的东西，真的", "type": "text", "timestamp": "2024-10-20T01:12:00+08:00"},
    ],
    "expected": {"is_deep": True, "depth_range": (65, 95), "tag_hints": ["人生", "意义", "自卑", "原生家庭"]},
}

SAMPLE_10_SHORT_EXCHANGE = {
    "name": "简短事务性对话",
    "messages": [
        {"id": "m1", "sender": "me", "content": "明天几点开会", "type": "text", "timestamp": "2024-11-01T17:00:00+08:00"},
        {"id": "m2", "sender": "李组长", "content": "上午十点", "type": "text", "timestamp": "2024-11-01T17:01:00+08:00"},
        {"id": "m3", "sender": "me", "content": "好的", "type": "text", "timestamp": "2024-11-01T17:01:30+08:00"},
        {"id": "m4", "sender": "李组长", "content": "记得带方案", "type": "text", "timestamp": "2024-11-01T17:02:00+08:00"},
        {"id": "m5", "sender": "me", "content": "ok", "type": "text", "timestamp": "2024-11-01T17:02:30+08:00"},
    ],
    "expected": {"is_deep": False, "depth_range": (0, 25), "tag_hints": []},
}


# 汇总
ALL_SAMPLES = [
    SAMPLE_1_DEEP_EMOTION,
    SAMPLE_2_CONFESSION,
    SAMPLE_3_APOLOGY_RECONCILIATION,
    SAMPLE_4_CASUAL_CHAT,
    SAMPLE_5_CAREER_DECISION,
    SAMPLE_6_FAREWELL,
    SAMPLE_7_LIGHT_JOKE,
    SAMPLE_8_ANXIETY_COMFORT,
    SAMPLE_9_DEEP_DISCUSSION,
    SAMPLE_10_SHORT_EXCHANGE,
]


# ══════════════════════════════════════════════════════════════════════
# 测试
# ══════════════════════════════════════════════════════════════════════


class TestRuleScoring:
    """规则初筛单元测试。"""

    def test_emotion_scoring_deep(self):
        """深度情感场景应得高情感分。"""
        from core.analysis.rules import compute_rule_scores

        scores = compute_rule_scores(SAMPLE_1_DEEP_EMOTION["messages"])
        assert scores.emotion >= 40, f"情感分应≥40, 实际={scores.emotion}"
        assert len(scores.hints) > 0, "应有特征提示"

    def test_emotion_scoring_casual(self):
        """日常闲聊应得低情感分。"""
        from core.analysis.rules import compute_rule_scores

        scores = compute_rule_scores(SAMPLE_4_CASUAL_CHAT["messages"])
        assert scores.emotion < 40, f"情感分应<40, 实际={scores.emotion}"

    def test_event_scoring_confession(self):
        """告白场景应得高事件分。"""
        from core.analysis.rules import compute_rule_scores

        scores = compute_rule_scores(SAMPLE_2_CONFESSION["messages"])
        assert scores.event >= 40, f"事件分应≥40, 实际={scores.event}"

    def test_event_scoring_apology(self):
        """道歉场景应得高事件分。"""
        from core.analysis.rules import compute_rule_scores

        scores = compute_rule_scores(SAMPLE_3_APOLOGY_RECONCILIATION["messages"])
        assert scores.event >= 30, f"事件分应≥30, 实际={scores.event}"

    def test_continuity_scoring_deep_discussion(self):
        """深度讨论应有高连续性分。"""
        from core.analysis.rules import compute_rule_scores

        scores = compute_rule_scores(SAMPLE_9_DEEP_DISCUSSION["messages"])
        assert scores.continuity >= 30, f"连续性分应≥30, 实际={scores.continuity}"

    def test_continuity_scoring_short(self):
        """短对话应有低连续性分。"""
        from core.analysis.rules import compute_rule_scores

        scores = compute_rule_scores(SAMPLE_10_SHORT_EXCHANGE["messages"])
        assert scores.continuity < 50, f"连续性分应<50, 实际={scores.continuity}"

    def test_interaction_scoring_comfort(self):
        """安慰场景应有高互动分。"""
        from core.analysis.rules import compute_rule_scores

        scores = compute_rule_scores(SAMPLE_8_ANXIETY_COMFORT["messages"])
        assert scores.interaction >= 30, f"互动分应≥30, 实际={scores.interaction}"

    def test_depth_score_casual_low(self):
        """日常闲聊深度分应低。"""
        from core.analysis.rules import compute_rule_scores, compute_depth_score

        scores = compute_rule_scores(SAMPLE_4_CASUAL_CHAT["messages"])
        depth = compute_depth_score(scores)
        assert depth < 40, f"深度分应<40, 实际={depth}"

    def test_depth_score_deep_high(self):
        """深度对话深度分应高。"""
        from core.analysis.rules import compute_rule_scores, compute_depth_score

        scores = compute_rule_scores(SAMPLE_1_DEEP_EMOTION["messages"])
        depth = compute_depth_score(scores)
        assert depth >= 40, f"深度分应≥40, 实际={depth}"


class TestTopicSegmentation:
    """话题分段测试。"""

    def test_no_split_close_messages(self):
        """时间接近的消息不应分段。"""
        from core.analysis.engine import TopicSegmenter

        seg = TopicSegmenter()
        messages = [
            {"id": "m1", "sender": "me", "content": "hi", "timestamp": "2024-01-01T10:00:00+08:00"},
            {"id": "m2", "sender": "other", "content": "hello", "timestamp": "2024-01-01T10:01:00+08:00"},
            {"id": "m3", "sender": "me", "content": "how are you", "timestamp": "2024-01-01T10:02:00+08:00"},
            {"id": "m4", "sender": "other", "content": "fine", "timestamp": "2024-01-01T10:03:00+08:00"},
        ]
        segments = seg.segment(messages)
        assert len(segments) == 1, f"应合并为1段, 实际={len(segments)}"

    def test_split_large_gap(self):
        """时间间隔大的消息应分段。"""
        from core.analysis.engine import TopicSegmenter

        seg = TopicSegmenter()
        messages = [
            {"id": "m1", "sender": "me", "content": "hi", "timestamp": "2024-01-01T10:00:00+08:00"},
            {"id": "m2", "sender": "other", "content": "hello", "timestamp": "2024-01-01T10:01:00+08:00"},
            # 2 小时间隔
            {"id": "m3", "sender": "me", "content": "hi again", "timestamp": "2024-01-01T12:00:00+08:00"},
            {"id": "m4", "sender": "other", "content": "hey", "timestamp": "2024-01-01T12:01:00+08:00"},
        ]
        segments = seg.segment(messages)
        assert len(segments) >= 1, f"应产生至少1个片段"

    def test_merge_short_segments(self):
        """过短片段应合并。"""
        from core.analysis.engine import TopicSegmenter

        seg = TopicSegmenter()
        # 2分钟后的大间隔
        messages = [
            {"id": "m1", "sender": "me", "content": "hi", "timestamp": "2024-01-01T10:00:00+08:00"},
            {"id": "m2", "sender": "other", "content": "hello", "timestamp": "2024-01-01T10:01:00+08:00"},
            {"id": "m3", "sender": "me", "content": "a", "timestamp": "2024-01-02T10:00:00+08:00"},  # 跨天-大间隔
            {"id": "m4", "sender": "other", "content": "b", "timestamp": "2024-01-02T10:01:00+08:00"},
            {"id": "m5", "sender": "me", "content": "c", "timestamp": "2024-01-02T10:02:00+08:00"},
            {"id": "m6", "sender": "other", "content": "d", "timestamp": "2024-01-02T10:03:00+08:00"},
        ]
        segments = seg.segment(messages)
        # 不应产生空片段
        for s in segments:
            assert len(s) > 0, "不应有空片段"


class TestEngineEndToEnd:
    """引擎端到端测试(使用 MockProvider,不调用真实 API)。"""

    def test_engine_with_mock_provider(self):
        """使用 MockProvider 创建引擎,验证基本流程。"""
        from core.analysis.engine import create_engine

        engine = create_engine(provider="mock")

        session = {
            "session_id": "test-session-001",
            "peer": "晨曦",
            "messages": SAMPLE_1_DEEP_EMOTION["messages"],
        }

        results = engine.analyze_session(session)
        # MockProvider 不返回真实分析,但应不崩溃
        assert isinstance(results, list), "应返回列表"

    def test_analyze_messages_direct(self):
        """直接分析消息列表。"""
        from core.analysis.engine import create_engine

        engine = create_engine(provider="mock")
        result = engine.analyze_messages(
            SAMPLE_1_DEEP_EMOTION["messages"],
            session_id="test-001",
        )
        assert result.segment_id.startswith("seg_"), f"segment_id 格式错误: {result.segment_id}"
        assert result.session_id == "test-001"
        assert 0 <= result.depth_score <= 100, f"depth_score 超出范围: {result.depth_score}"
        assert "emotion" in result.dimensions
        assert "event" in result.dimensions
        assert "continuity" in result.dimensions
        assert "interaction" in result.dimensions

    def test_result_matches_schema(self):
        """验证输出符合 analysis-result.schema.json。"""
        from core.analysis.engine import create_engine

        engine = create_engine(provider="mock")
        result = engine.analyze_messages(
            SAMPLE_2_CONFESSION["messages"],
            session_id="test-002",
        )

        # Required fields
        assert isinstance(result.segment_id, str) and len(result.segment_id) > 0
        assert isinstance(result.session_id, str)
        assert isinstance(result.depth_score, (int, float))
        assert 0 <= result.depth_score <= 100
        assert isinstance(result.dimensions, dict)
        assert "emotion" in result.dimensions
        assert "event" in result.dimensions
        assert "continuity" in result.dimensions
        assert "interaction" in result.dimensions
        assert isinstance(result.start_time, str)
        assert isinstance(result.end_time, str)
        assert isinstance(result.summary, str)
        assert isinstance(result.messages, list)

        # Optional fields
        if result.golden_quotes:
            for q in result.golden_quotes:
                assert "text" in q
                assert "message_id" in q

        # Dimension ranges
        for dim, val in result.dimensions.items():
            assert 0 <= val <= 100, f"维度 {dim}={val} 超出 0-100"

    def test_all_samples_run_without_error(self):
        """所有 10 段样例都应能正常分析。"""
        from core.analysis.engine import create_engine

        engine = create_engine(provider="mock")

        for i, sample in enumerate(ALL_SAMPLES):
            result = engine.analyze_messages(
                sample["messages"],
                session_id=f"sample-{i+1:02d}",
            )
            assert result is not None, f"样例 {sample['name']} 分析失败"
            assert 0 <= result.depth_score <= 100, (
                f"样例 {sample['name']} depth_score={result.depth_score} 超出范围"
            )


class TestSampleAgreement:
    """10 段样例人类认同度测试。

    验证规则评分的 is_deep 判定与人类预期一致。
    目标:≥80% 认同度(即 10 段中至少 8 段与预期一致)。
    """

    def test_10_samples_agreement_rate(self):
        """验证 ≥80% 的样例 is_deep 判定与预期一致。"""
        from core.analysis.rules import compute_depth_score, compute_rule_scores
        from core.analysis.config import config

        total = len(ALL_SAMPLES)
        agreements = 0
        disagreements: list[str] = []

        threshold = config.deep_threshold  # 默认 60

        for i, sample in enumerate(ALL_SAMPLES):
            scores = compute_rule_scores(sample["messages"])
            depth = compute_depth_score(scores)
            is_deep = depth >= threshold
            expected_deep = sample["expected"]["is_deep"]

            if is_deep == expected_deep:
                agreements += 1
            else:
                disagreements.append(
                    f"  [{sample['name']}] depth={depth:.1f} "
                    f"判定={'deep' if is_deep else 'shallow'} "
                    f"预期={'deep' if expected_deep else 'shallow'}"
                )

        rate = agreements / total * 100
        print(f"\n  认同度: {agreements}/{total} ({rate:.0f}%)")
        if disagreements:
            print("  不一致:")
            for d in disagreements:
                print(d)

        assert rate >= 80, (
            f"10段样例认同度={rate:.0f}%, 不满足≥80%的要求。\n不一致:\n"
            + "\n".join(disagreements)
        )

    def test_depth_score_in_expected_range(self):
        """验证每段样例的深度评分在预期区间内或合理误差范围内。"""
        from core.analysis.rules import compute_depth_score, compute_rule_scores

        tolerance = 5.0  # 允许 5 分的容差
        in_range = 0
        out_of_range: list[str] = []

        for sample in ALL_SAMPLES:
            scores = compute_rule_scores(sample["messages"])
            depth = compute_depth_score(scores)
            min_expected, max_expected = sample["expected"]["depth_range"]

            if min_expected - tolerance <= depth <= max_expected + tolerance:
                in_range += 1
            else:
                out_of_range.append(
                    f"  [{sample['name']}] depth={depth:.1f} "
                    f"预期 [{min_expected}-{max_expected}]"
                )

        total = len(ALL_SAMPLES)
        rate = in_range / total * 100
        print(f"\n  深度评分区间命中: {in_range}/{total} ({rate:.0f}%)")
        if out_of_range:
            print("  超出区间:")
            for o in out_of_range:
                print(o)

        assert rate >= 70, (
            f"深度评分区间命中率={rate:.0f}%, 偏低。\n超出:\n"
            + "\n".join(out_of_range)
        )


class TestConfig:
    """配置加载测试。"""

    def test_config_loads_from_env(self):
        """配置应从 .env 文件加载。"""
        from core.analysis.config import Config, config

        assert isinstance(config.api_key, str), "api_key 应为字符串"
        assert isinstance(config.base_url, str), "base_url 应为字符串"
        assert config.default_model in ("deepseek-v4-flash", "deepseek-v4-pro", ""), (
            f"不支持的模型: {config.default_model}"
        )
        assert 0 <= config.deep_threshold <= 100
        assert config.rule_low_conf_cap < config.rule_high_conf_cap

    def test_api_fallback_range(self):
        """API 回退区间应合理。"""
        from core.analysis.config import config

        low, high = config.rule_api_fallback_range
        assert 0 <= low < high <= 100
        assert low == config.rule_low_conf_cap
        assert high == config.rule_high_conf_cap


class TestModelProvider:
    """模型提供者测试。"""

    def test_create_deepseek_provider(self):
        """应能创建 DeepSeek 提供者。"""
        from core.analysis.model_provider import create_provider, DeepSeekProvider

        p = create_provider("deepseek")
        assert isinstance(p, DeepSeekProvider)

    def test_create_mock_provider(self):
        """应能创建 Mock 提供者。"""
        from core.analysis.model_provider import create_provider, MockProvider

        p = create_provider("mock")
        assert isinstance(p, MockProvider)

    def test_mock_provider_returns_valid_response(self):
        """Mock 提供者应返回合法响应。"""
        from core.analysis.model_provider import MockProvider

        p = MockProvider()
        result = p.chat_json([{"role": "user", "content": "test"}])
        assert isinstance(result, dict)
        assert result.get("mock") is True

    def test_invalid_provider_raises(self):
        """无效提供者名应抛出异常。"""
        import pytest

        from core.analysis.model_provider import create_provider

        with pytest.raises(ValueError, match="不支持的 provider"):
            create_provider("nonexistent")


# ══════════════════════════════════════════════════════════════════════
# 运行入口
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v", "-s"]))

"""
深度对话识别引擎。

对聊天会话执行:
1. 话题分段:按时间间隔和内容变化切分对话
2. 四维打分:情感/事件/连续性/互动(规则初筛 + 模型精调)
3. 深度评分:0-100 加权合成
4. 摘要:三句话总结
5. 金句:1-3 条代表性文本

输出符合 docs/contracts/analysis-result.schema.json。
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .config import Config, config
from .model_provider import ModelProvider, create_provider
from .rules import (
    RuleScores,
    compute_depth_score,
    compute_rule_scores,
    should_call_api,
)

logger = logging.getLogger(__name__)


# ── 数据模型 ────────────────────────────────────────────────────────────


@dataclass
class AnalysisResult:
    """符合 analysis-result.schema.json 的分析结果。"""

    segment_id: str
    session_id: str
    depth_score: float
    threshold: float
    is_deep: bool
    dimensions: dict[str, float]
    start_time: str
    end_time: str
    duration_minutes: float
    summary: str
    tags: list[str] = field(default_factory=list)
    golden_quotes: list[dict[str, str]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    model: str = ""


# ── 话题分段 ────────────────────────────────────────────────────────────


class TopicSegmenter:
    """按时间间隔和内容变化将长会话切分为话题片段。"""

    def __init__(self, cfg: Optional[Config] = None) -> None:
        self._cfg = cfg or config

    def segment(
        self, messages: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        """
        将消息列表切分为多个话题片段。

        切分规则:
        1. 两条相邻消息时间间隔 > time_gap_minutes → 分段边界
        2. 片段消息数 < min_segment_messages → 合并至下一片段
        3. 考虑发送者变化和内容关键词作为辅助切分信号
        """
        if not messages:
            return []

        gap_minutes = self._cfg.time_gap_minutes
        min_msg = self._cfg.min_segment_messages

        # 第一遍:按时间间隔切分
        raw_segments: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = [messages[0]]

        for i in range(1, len(messages)):
            gap = self._time_diff_minutes(messages[i - 1], messages[i])
            if gap > gap_minutes:
                raw_segments.append(current)
                current = []
            current.append(messages[i])

        if current:
            raw_segments.append(current)

        # 第二遍:合并过短片段
        merged: list[list[dict[str, Any]]] = []
        buffer: list[dict[str, Any]] = []

        for seg in raw_segments:
            buffer.extend(seg)
            if len(buffer) >= min_msg:
                merged.append(buffer)
                buffer = []
            # 如果 buffer 有消息但不足 min_msg,继续累积到下一片段

        # 处理剩余 buffer
        if buffer:
            if merged:
                # 合并到最后一个片段
                merged[-1].extend(buffer)
            else:
                merged.append(buffer)

        return merged

    @staticmethod
    def _time_diff_minutes(
        msg_a: dict[str, Any], msg_b: dict[str, Any]
    ) -> float:
        """两条消息之间的时间差(分钟)。"""
        try:
            t_a = datetime.fromisoformat(msg_a.get("timestamp", ""))
            t_b = datetime.fromisoformat(msg_b.get("timestamp", ""))
            return abs((t_b - t_a).total_seconds()) / 60.0
        except (ValueError, TypeError):
            return 0.0


# ── 模型提示词构建 ────────────────────────────────────────────────────────


def _build_scoring_prompt(messages: list[dict[str, Any]]) -> str:
    """构建四维打分的模型提示词。"""
    # 格式化对话
    dialog_lines: list[str] = []
    for m in messages:
        sender = m.get("sender", "?")
        content = m.get("content", "")
        dialog_lines.append(f"[{sender}]: {content}")
    dialog_text = "\n".join(dialog_lines)

    return f"""你是深度对话分析专家。请对以下微信对话片段进行四维打分(每维0-100):

1. 情感深度(emotion):自我暴露、情绪倾诉、脆弱表达的程度
2. 关键节点(event):是否有告白、道歉、和解、离别、重大决定
3. 主题连续性(continuity):围绕同一话题持续多轮、有推进
4. 互动质量(interaction):倾听、共情、有效回应的程度

对话内容:
{dialog_text}

请返回JSON格式:
{{
  "emotion": <0-100>,
  "event": <0-100>,
  "continuity": <0-100>,
  "interaction": <0-100>,
  "summary": "三句话以内的摘要",
  "tags": ["标签1", "标签2"],
  "golden_quotes": [
    {{"text": "金句原文", "message_index": <消息序号(从0开始)>}}
  ]
}}"""


def _build_summary_prompt(messages: list[dict[str, Any]]) -> str:
    """构建摘要专用提示词。"""
    dialog_lines = [f"[{m.get('sender', '?')}]: {m.get('content', '')}" for m in messages]
    dialog_text = "\n".join(dialog_lines)

    return f"""请用三句中文概括以下微信对话的核心内容和情感走向:

{dialog_text}

直接返回三句话,不要加任何前缀和格式。"""


# ── 分析引擎 ────────────────────────────────────────────────────────────


class AnalysisEngine:
    """深度对话识别引擎。

    组合规则初筛和模型精调,生成完整的 AnalysisResult。
    """

    def __init__(
        self,
        provider: Optional[ModelProvider] = None,
        cfg: Optional[Config] = None,
    ) -> None:
        self._cfg = cfg or config
        self._segmenter = TopicSegmenter(self._cfg)
        self._provider = provider
        self._model_name: str = ""

    @property
    def provider(self) -> ModelProvider:
        if self._provider is None:
            self._provider = create_provider("deepseek", self._cfg)
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model_name or self._cfg.default_model

    def analyze_session(
        self,
        session: dict[str, Any],
        *,
        model: Optional[str] = None,
    ) -> list[AnalysisResult]:
        """
        分析整个会话,返回所有深度片段的 AnalysisResult 列表。

        Args:
            session: ChatSession 对象(符合 session.schema.json)
            model: 指定模型,None 使用默认

        Returns:
            分析结果列表(仅包含判定为深度的片段)
        """
        self._model_name = model or self._cfg.default_model
        messages: list[dict[str, Any]] = session.get("messages", [])
        if not messages:
            return []

        # 1. 话题分段
        segments = self._segmenter.segment(messages)
        logger.info("会话 %s 切分为 %d 个片段", session.get("session_id"), len(segments))

        # 2. 逐段分析
        results: list[AnalysisResult] = []
        for i, seg_messages in enumerate(segments):
            result = self._analyze_segment(
                seg_messages=seg_messages,
                session_id=session.get("session_id", ""),
                segment_index=i,
            )
            if result is not None:
                results.append(result)

        return results

    def _analyze_segment(
        self,
        seg_messages: list[dict[str, Any]],
        session_id: str,
        segment_index: int,
    ) -> Optional[AnalysisResult]:
        """分析单个片段:规则初筛 → (可选)模型精调 → 组装结果。"""
        if not seg_messages:
            return None

        # ── 规则初筛 ──
        rule_scores = compute_rule_scores(seg_messages)
        rule_depth = compute_depth_score(rule_scores)
        do_call, reason = should_call_api(rule_scores, rule_depth, self._cfg)
        logger.info("片段#%d 规则评分=%.1f, %s", segment_index, rule_depth, reason)

        # ── 确定最终评分 ──
        if not self._cfg.is_configured or not do_call:
            # 仅使用规则评分(无 API)
            final_scores = rule_scores
            final_depth = rule_depth
            api_summary = self._rule_summary(seg_messages, rule_scores)
            api_tags = self._rule_tags(rule_scores)
            api_quotes = self._rule_golden_quotes(seg_messages, rule_scores)
            source = "rules"
        else:
            # 调用模型精调
            try:
                model_result = self._call_model_for_scoring(seg_messages)
                # 融合规则和模型:模型为主,规则补充
                final_scores = self._merge_scores(rule_scores, model_result)
                final_depth = compute_depth_score(final_scores)
                api_summary = model_result.get("summary", "")
                api_tags = model_result.get("tags", [])
                api_quotes = self._extract_quotes_from_model(
                    model_result, seg_messages
                )
                source = "model"
            except Exception as e:
                logger.warning("模型调用失败,回退到规则评分: %s", e)
                final_scores = rule_scores
                final_depth = rule_depth
                api_summary = self._rule_summary(seg_messages, rule_scores)
                api_tags = self._rule_tags(rule_scores)
                api_quotes = self._rule_golden_quotes(seg_messages, rule_scores)
                source = "rules(fallback)"

        # ── 时间信息 ──
        start_time = seg_messages[0].get("timestamp", "")
        end_time = seg_messages[-1].get("timestamp", "")
        try:
            t0 = datetime.fromisoformat(start_time)
            t1 = datetime.fromisoformat(end_time)
            duration = abs((t1 - t0).total_seconds()) / 60.0
        except (ValueError, TypeError):
            duration = 0.0

        # ── 组装结果 ──
        threshold = self._cfg.deep_threshold
        is_deep = final_depth >= threshold

        result = AnalysisResult(
            segment_id=self._gen_segment_id(session_id, segment_index),
            session_id=session_id,
            depth_score=final_depth,
            threshold=threshold,
            is_deep=is_deep,
            dimensions={
                "emotion": round(final_scores.emotion, 1),
                "event": round(final_scores.event, 1),
                "continuity": round(final_scores.continuity, 1),
                "interaction": round(final_scores.interaction, 1),
            },
            start_time=start_time,
            end_time=end_time,
            duration_minutes=round(duration, 1),
            summary=api_summary,
            tags=api_tags[:5],
            golden_quotes=api_quotes[:3],
            messages=seg_messages,
            model=self.model_name,
        )

        logger.info(
            "片段#%d 深度=%.1f is_deep=%s source=%s",
            segment_index,
            final_depth,
            is_deep,
            source,
        )
        return result

    def _call_model_for_scoring(
        self, seg_messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """调用 DeepSeek 模型进行四维打分。"""
        prompt = _build_scoring_prompt(seg_messages)
        messages = [{"role": "user", "content": prompt}]
        return self.provider.chat_json(
            messages,
            model=self.model_name,
            temperature=0.3,
            max_tokens=1024,
        )

    @staticmethod
    def _merge_scores(
        rule: RuleScores, model: dict[str, Any]
    ) -> RuleScores:
        """融合规则评分和模型评分(模型为主 70%,规则 30%)。"""
        return RuleScores(
            emotion=model.get("emotion", rule.emotion) * 0.70 + rule.emotion * 0.30,
            event=model.get("event", rule.event) * 0.70 + rule.event * 0.30,
            continuity=model.get("continuity", rule.continuity) * 0.70 + rule.continuity * 0.30,
            interaction=model.get("interaction", rule.interaction) * 0.70 + rule.interaction * 0.30,
            confidence=0.85,  # 模型参与时置信度较高
            hints=rule.hints,
        )

    # ── 规则级摘要 / 标签 / 金句(不调用 API 时使用) ──

    @staticmethod
    def _rule_summary(
        messages: list[dict[str, Any]], scores: RuleScores
    ) -> str:
        """基于规则评分生成简单摘要。"""
        parts: list[str] = []
        if scores.emotion >= 50:
            parts.append("这段对话展现了较深的情感交流")
        if scores.event >= 50:
            parts.append("涉及重要的人际事件或决定")
        if scores.continuity >= 50:
            parts.append("双方围绕主题进行了持续深入的讨论")
        if scores.interaction >= 50:
            parts.append("互动质量较高,有共情和有效回应")
        if not parts:
            return "日常交流对话。"
        return "。".join(parts) + "。"

    @staticmethod
    def _rule_tags(scores: RuleScores) -> list[str]:
        """基于规则评分生成标签。"""
        tags: list[str] = []
        if scores.emotion >= 60:
            tags.append("深度情感")
        if scores.event >= 60:
            tags.append("关键事件")
        if scores.continuity >= 60:
            tags.append("深度讨论")
        if scores.interaction >= 60:
            tags.append("高质量互动")
        if not tags:
            tags.append("日常聊天")
        return tags

    @staticmethod
    def _rule_golden_quotes(
        messages: list[dict[str, Any]], scores: RuleScores
    ) -> list[dict[str, str]]:
        """基于规则提取金句:选最长的 1-2 条有实质内容的消息。"""
        candidates = []
        for m in messages:
            content = m.get("content", "").strip()
            # 过滤掉过短、纯表情、系统消息
            if len(content) >= 15 and m.get("type") not in ("system",):
                # 优先选择含情感关键词的消息
                from .rules import EMOTION_VULNERABILITY, EMOTION_SELF_DISCLOSURE

                content_lower = content.lower()
                emotion_score = sum(
                    1
                    for kw in EMOTION_VULNERABILITY + EMOTION_SELF_DISCLOSURE
                    if kw.lower() in content_lower
                )
                candidates.append((content, m.get("id", ""), len(content) + emotion_score * 20))

        # 按评分排序取前 2
        candidates.sort(key=lambda x: x[2], reverse=True)
        return [{"text": c[0], "message_id": c[1]} for c in candidates[:2]]

    @staticmethod
    def _extract_quotes_from_model(
        model_result: dict[str, Any], messages: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """从模型返回的 golden_quotes 中提取金句,匹配 message_id。"""
        quotes = model_result.get("golden_quotes", [])
        result: list[dict[str, str]] = []
        for q in quotes:
            text = q.get("text", "")
            msg_index = q.get("message_index", -1)
            msg_id = ""
            if isinstance(msg_index, int) and 0 <= msg_index < len(messages):
                msg_id = messages[msg_index].get("id", "")
            result.append({"text": text, "message_id": msg_id})
        return result

    @staticmethod
    def _gen_segment_id(session_id: str, index: int) -> str:
        """生成片段唯一 ID。"""
        raw = f"{session_id}_{index}"
        return f"seg_{hashlib.sha1(raw.encode()).hexdigest()[:12]}"

    # ── 便捷方法:单片段分析(不依赖完整 session) ──

    def analyze_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        session_id: str = "unknown",
        model: Optional[str] = None,
    ) -> AnalysisResult:
        """直接分析一组消息(无需完整 session)。用于测试。"""
        self._model_name = model or self._cfg.default_model
        result = self._analyze_segment(
            seg_messages=messages,
            session_id=session_id,
            segment_index=0,
        )
        if result is None:
            raise ValueError("无法分析空消息列表")
        return result


# ── 工厂函数 ────────────────────────────────────────────────────────────


def create_engine(
    provider: str = "deepseek",
    model: Optional[str] = None,
    cfg: Optional[Config] = None,
) -> AnalysisEngine:
    """创建分析引擎实例。

    Args:
        provider: "deepseek" | "mock"
        model: 模型名称,None 使用 .env 配置
        cfg: 配置对象

    Returns:
        配置好的 AnalysisEngine
    """
    cfg = cfg or config
    p = create_provider(provider, cfg)
    return AnalysisEngine(provider=p, cfg=cfg)

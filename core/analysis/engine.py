# -*- coding: utf-8 -*-
"""深度对话识别引擎。"""

from __future__ import absolute_import

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import Config, config
from .model_provider import ModelProvider, create_provider
from .rules import RuleScores, compute_depth_score, compute_rule_scores, should_call_api

logger = logging.getLogger(__name__)


class AnalysisResult(object):
    def __init__(self, segment_id="", session_id="", depth_score=0.0, threshold=60.0,
                 is_deep=False, dimensions=None, start_time="", end_time="",
                 duration_minutes=0.0, summary="", tags=None, golden_quotes=None,
                 messages=None, model=""):
        self.segment_id = segment_id
        self.session_id = session_id
        self.depth_score = depth_score
        self.threshold = threshold
        self.is_deep = is_deep
        self.dimensions = dimensions or {"emotion": 0.0, "event": 0.0,
                                          "continuity": 0.0, "interaction": 0.0}
        self.start_time = start_time
        self.end_time = end_time
        self.duration_minutes = duration_minutes
        self.summary = summary
        self.tags = tags or []
        self.golden_quotes = golden_quotes or []
        self.messages = messages or []
        self.model = model


class TopicSegmenter(object):
    def __init__(self, cfg=None):
        self._cfg = cfg or config

    @staticmethod
    def _parse_iso(ts_str):
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

    @staticmethod
    def _time_diff_minutes(msg_a, msg_b):
        try:
            t_a = TopicSegmenter._parse_iso(msg_a.get("timestamp", ""))
            t_b = TopicSegmenter._parse_iso(msg_b.get("timestamp", ""))
            if t_a is None or t_b is None:
                return 0.0
            return abs((t_b - t_a).total_seconds()) / 60.0
        except (ValueError, TypeError, AttributeError):
            return 0.0

    def segment(self, messages):
        if not messages:
            return []
        gap_minutes = self._cfg.time_gap_minutes
        min_msg = self._cfg.min_segment_messages
        raw_segments = []
        current = [messages[0]]
        for i in range(1, len(messages)):
            gap = self._time_diff_minutes(messages[i - 1], messages[i])
            if gap > gap_minutes:
                raw_segments.append(current)
                current = []
            current.append(messages[i])
        if current:
            raw_segments.append(current)
        merged = []
        buffer = []
        for seg in raw_segments:
            buffer.extend(seg)
            if len(buffer) >= min_msg:
                merged.append(buffer)
                buffer = []
        if buffer:
            if merged:
                merged[-1].extend(buffer)
            else:
                merged.append(buffer)
        return merged


def _build_scoring_prompt(messages):
    dialog_lines = ["[{}]: {}".format(m.get("sender", "?"), m.get("content", "")) for m in messages]
    dialog_text = "\n".join(dialog_lines)
    return (
        "你是深度对话分析专家。请对以下微信对话片段进行四维打分(每维0-100):\n\n"
        "1. 情感深度(emotion):自我暴露、情绪倾诉、脆弱表达的程度\n"
        "2. 关键节点(event):是否有告白、道歉、和解、离别、重大决定\n"
        "3. 主题连续性(continuity):围绕同一话题持续多轮、有推进\n"
        "4. 互动质量(interaction):倾听、共情、有效回应的程度\n\n"
        "对话内容:\n{}\n\n"
        "请返回JSON:\n"
        '{{"emotion": 0-100, "event": 0-100, "continuity": 0-100, '
        '"interaction": 0-100, "summary": "...", "tags": [...], '
        '"golden_quotes": [{{"text": "...", "message_index": 0}}]}}'
    ).format(dialog_text)


class AnalysisEngine(object):
    def __init__(self, provider=None, cfg=None):
        self._cfg = cfg or config
        self._segmenter = TopicSegmenter(self._cfg)
        self._provider = provider
        self._model_name = ""

    @property
    def provider(self):
        if self._provider is None:
            self._provider = create_provider("deepseek", self._cfg)
        return self._provider

    @property
    def model_name(self):
        return self._model_name or self._cfg.default_model

    def analyze_session(self, session, model=None):
        self._model_name = model or self._cfg.default_model
        messages = session.get("messages", [])
        if not messages:
            return []
        segments = self._segmenter.segment(messages)
        logger.info("session %s -> %d segments", session.get("session_id"), len(segments))
        results = []
        for i, seg_msgs in enumerate(segments):
            r = self._analyze_segment(seg_msgs, session.get("session_id", ""), i)
            if r is not None:
                results.append(r)
        return results

    def _analyze_segment(self, seg_messages, session_id, segment_index):
        if not seg_messages:
            return None
        rule_scores = compute_rule_scores(seg_messages)
        rule_depth = compute_depth_score(rule_scores)
        do_call, reason = should_call_api(rule_scores, rule_depth, self._cfg)
        logger.info("seg#%d rule=%.1f %s", segment_index, rule_depth, reason)

        if not self._cfg.is_configured or not do_call:
            final_scores = rule_scores
            final_depth = rule_depth
            api_summary = self._rule_summary(seg_messages, rule_scores)
            api_tags = self._rule_tags(rule_scores)
            api_quotes = self._rule_golden_quotes(seg_messages, rule_scores)
        else:
            try:
                model_result = self._call_model_for_scoring(seg_messages)
                final_scores = self._merge_scores(rule_scores, model_result)
                final_depth = compute_depth_score(final_scores)
                api_summary = model_result.get("summary", "")
                api_tags = model_result.get("tags", [])
                api_quotes = self._extract_quotes_from_model(model_result, seg_messages)
            except Exception as e:
                logger.warning("model call failed, fallback: %s", e)
                final_scores = rule_scores
                final_depth = rule_depth
                api_summary = self._rule_summary(seg_messages, rule_scores)
                api_tags = self._rule_tags(rule_scores)
                api_quotes = self._rule_golden_quotes(seg_messages, rule_scores)

        start_time = seg_messages[0].get("timestamp", "")
        end_time = seg_messages[-1].get("timestamp", "")
        try:
            t0 = TopicSegmenter._parse_iso(start_time)
            t1 = TopicSegmenter._parse_iso(end_time)
            duration = abs((t1 - t0).total_seconds()) / 60.0 if (t0 and t1) else 0.0
        except (ValueError, TypeError, AttributeError):
            duration = 0.0

        threshold = self._cfg.deep_threshold
        is_deep = final_depth >= threshold
        return AnalysisResult(
            segment_id=self._gen_segment_id(session_id, segment_index),
            session_id=session_id,
            depth_score=final_depth,
            threshold=threshold,
            is_deep=is_deep,
            dimensions={"emotion": round(final_scores.emotion, 1),
                        "event": round(final_scores.event, 1),
                        "continuity": round(final_scores.continuity, 1),
                        "interaction": round(final_scores.interaction, 1)},
            start_time=start_time, end_time=end_time,
            duration_minutes=round(duration, 1),
            summary=api_summary, tags=api_tags[:5],
            golden_quotes=api_quotes[:3], messages=seg_messages,
            model=self.model_name,
        )

    def _call_model_for_scoring(self, seg_messages):
        return self.provider.chat_json(
            [{"role": "user", "content": _build_scoring_prompt(seg_messages)}],
            model=self.model_name, temperature=0.3, max_tokens=1024)

    @staticmethod
    def _merge_scores(rule, model):
        return RuleScores(
            emotion=model.get("emotion", rule.emotion) * 0.70 + rule.emotion * 0.30,
            event=model.get("event", rule.event) * 0.70 + rule.event * 0.30,
            continuity=model.get("continuity", rule.continuity) * 0.70 + rule.continuity * 0.30,
            interaction=model.get("interaction", rule.interaction) * 0.70 + rule.interaction * 0.30,
            confidence=0.85, hints=rule.hints)

    @staticmethod
    def _rule_summary(messages, scores):
        parts = []
        if scores.emotion >= 50:
            parts.append("这段对话展现了较深的情感交流")
        if scores.event >= 50:
            parts.append("涉及重要的人际事件或决定")
        if scores.continuity >= 50:
            parts.append("双方围绕主题进行了持续深入的讨论")
        if scores.interaction >= 50:
            parts.append("互动质量较高,有共情和有效回应")
        return "。".join(parts) + "。" if parts else "日常交流对话。"

    @staticmethod
    def _rule_tags(scores):
        tags = []
        if scores.emotion >= 60:
            tags.append("深度情感")
        if scores.event >= 60:
            tags.append("关键事件")
        if scores.continuity >= 60:
            tags.append("深度讨论")
        if scores.interaction >= 60:
            tags.append("高质量互动")
        return tags if tags else ["日常聊天"]

    @staticmethod
    def _rule_golden_quotes(messages, scores):
        from .rules import EMOTION_VULNERABILITY, EMOTION_SELF_DISCLOSURE
        candidates = []
        for m in messages:
            content = m.get("content", "").strip()
            if len(content) >= 15 and m.get("type") not in ("system",):
                content_lower = content.lower()
                emotion_score = sum(1 for kw in EMOTION_VULNERABILITY + EMOTION_SELF_DISCLOSURE
                                    if kw.lower() in content_lower)
                candidates.append((content, m.get("id", ""), len(content) + emotion_score * 20))
        candidates.sort(key=lambda x: x[2], reverse=True)
        return [{"text": c[0], "message_id": c[1]} for c in candidates[:2]]

    @staticmethod
    def _extract_quotes_from_model(model_result, messages):
        quotes = model_result.get("golden_quotes", [])
        result = []
        for q in quotes:
            msg_index = q.get("message_index", -1)
            msg_id = ""
            if isinstance(msg_index, int) and 0 <= msg_index < len(messages):
                msg_id = messages[msg_index].get("id", "")
            result.append({"text": q.get("text", ""), "message_id": msg_id})
        return result

    @staticmethod
    def _gen_segment_id(session_id, index):
        return "seg_" + hashlib.sha1("{}_{}".format(session_id, index).encode()).hexdigest()[:12]

    def analyze_messages(self, messages, session_id="unknown", model=None):
        self._model_name = model or self._cfg.default_model
        result = self._analyze_segment(messages, session_id, 0)
        if result is None:
            raise ValueError("无法分析空消息列表")
        return result


def create_engine(provider="deepseek", model=None, cfg=None):
    cfg = cfg or config
    p = create_provider(provider, cfg)
    return AnalysisEngine(provider=p, cfg=cfg)

# -*- coding: utf-8 -*-
"""DeepTalk 深度对话识别引擎。"""

from .config import Config, config
from .engine import AnalysisEngine, AnalysisResult, create_engine
from .model_provider import DeepSeekProvider, MockProvider, ModelProvider, create_provider
from .rules import RuleScores, compute_depth_score, compute_rule_scores, should_call_api

__all__ = [
    "AnalysisEngine", "AnalysisResult", "Config", "config",
    "DeepSeekProvider", "MockProvider", "ModelProvider",
    "RuleScores", "compute_depth_score", "compute_rule_scores",
    "create_engine", "create_provider", "should_call_api",
]

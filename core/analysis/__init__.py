"""
DeepTalk 深度对话识别引擎。

核心模块:
- engine: 分析引擎(分段 / 打分 / 摘要 / 金句)
- model_provider: 模型接入抽象层(DeepSeek API)
- rules: 规则初筛引擎(本地,减少 API 调用)
- config: 全局配置(从 .env 读取)
"""

from .config import Config, config
from .engine import AnalysisEngine, AnalysisResult, create_engine
from .model_provider import (
    DeepSeekProvider,
    MockProvider,
    ModelProvider,
    create_provider,
)
from .rules import (
    RuleScores,
    compute_depth_score,
    compute_rule_scores,
    should_call_api,
)

__all__ = [
    "AnalysisEngine",
    "AnalysisResult",
    "Config",
    "config",
    "DeepSeekProvider",
    "MockProvider",
    "ModelProvider",
    "RuleScores",
    "compute_depth_score",
    "compute_rule_scores",
    "create_engine",
    "create_provider",
    "should_call_api",
]

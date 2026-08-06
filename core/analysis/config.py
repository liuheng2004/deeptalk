"""
DeepTalk 分析引擎配置。

从项目根目录的 .env 文件加载 DeepSeek API 密钥与端点,
提供模型切换、评分阈值等配置项。
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _find_env_file() -> Optional[Path]:
    """向上查找 .env 文件,直到到达项目根目录。"""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / ".env",  # deeptalk/.env
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _load_env() -> dict[str, str]:
    """手动解析 .env 文件(无依赖),返回键值字典。"""
    env: dict[str, str] = {}
    env_file = _find_env_file()
    if env_file is None:
        return env

    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                env[key] = value
    return env


# 加载一次,后续通过 Config 实例使用
_env = _load_env()


@dataclass
class Config:
    """分析引擎全局配置。"""

    # --- API 配置 ---
    api_key: str = field(default_factory=lambda: _env.get("DEEPSEEK_API_KEY", ""))
    base_url: str = field(
        default_factory=lambda: _env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )

    # --- 模型配置 ---
    default_model: str = field(
        default_factory=lambda: _env.get("DEEPTALK_MODEL", "deepseek-v4-flash")
    )

    # --- 评分阈值 ---
    deep_threshold: float = 60.0
    """depth_score >= 此值判定为深度对话。"""

    # --- 规则初筛 ---
    rule_low_conf_cap: float = 40.0
    """规则评分低于此值,直接跳过 API,判定非深度。"""
    rule_high_conf_cap: float = 80.0
    """规则评分高于此值,可跳过 API,判定为深度(节省调用)。"""
    rule_api_fallback_range: tuple[float, float] = (40.0, 80.0)
    """规则评分在此区间内,需调用模型确认。"""

    # --- 分段 ---
    time_gap_minutes: int = 30
    """两条消息间隔超过此分钟数,视为话题分段边界。"""
    min_segment_messages: int = 4
    """一个片段至少包含的消息数(不足则合并至下一片段)。"""

    # --- API 调用配置 ---
    api_timeout_seconds: int = 60
    api_max_retries: int = 2

    @property
    def is_configured(self) -> bool:
        """是否已配置有效的 API Key。"""
        return bool(self.api_key and self.api_key != "your-api-key-here")


# 全局单例
config = Config()

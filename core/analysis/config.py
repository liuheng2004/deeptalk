# -*- coding: utf-8 -*-
"""
DeepTalk 分析引擎配置。

从项目根目录的 .env 文件加载 DeepSeek API 密钥与端点,
提供模型切换、评分阈值等配置项。
"""

import os
from pathlib import Path
from typing import Optional, Tuple


def _find_env_file():
    # type: () -> Optional[Path]
    candidates = [
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _load_env():
    # type: () -> dict
    env = {}
    env_file = _find_env_file()
    if env_file is None:
        return env
    with open(str(env_file), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
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


_env = None  # type: Optional[dict]


def _get_env():
    global _env
    if _env is None:
        _env = _load_env()
    return _env


class Config(object):
    def __init__(self):
        env = _get_env()
        self.api_key = env.get("DEEPSEEK_API_KEY", "")
        self.base_url = env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.default_model = env.get("DEEPTALK_MODEL", "deepseek-v4-flash")

        self.deep_threshold = 60.0
        self.rule_low_conf_cap = 40.0
        self.rule_high_conf_cap = 80.0
        self.rule_api_fallback_range = (40.0, 80.0)  # type: Tuple[float, float]

        self.time_gap_minutes = 30
        self.min_segment_messages = 4
        self.api_timeout_seconds = 60
        self.api_max_retries = 2

    @property
    def is_configured(self):
        return bool(self.api_key and self.api_key != "your-api-key-here")


config = Config()

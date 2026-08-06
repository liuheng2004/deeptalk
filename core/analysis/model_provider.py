"""
模型接入抽象层。

提供统一的模型调用接口,默认使用 deepseek-v4-flash,
支持切换到 deepseek-v4-pro 或其他兼容 OpenAI API 的模型。

密钥从 .env 读取,不硬编码。
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from .config import Config, config

logger = logging.getLogger(__name__)


class ModelProvider(ABC):
    """模型提供者抽象基类。"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        发送对话并返回模型响应文本。

        Args:
            messages: OpenAI 格式的消息列表 [{"role": "user", "content": "..."}]
            model: 模型名称,None 则使用默认模型
            temperature: 采样温度(0-2)
            max_tokens: 最大输出 token 数
            response_format: 如 {"type": "json_object"} 强制 JSON 输出

        Returns:
            模型响应的文本内容
        """
        ...

    @abstractmethod
    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """
        发送对话并返回解析后的 JSON 对象。

        要求模型返回合法的 JSON;解析失败将抛出异常。
        """
        ...


class DeepSeekProvider(ModelProvider):
    """DeepSeek API 提供者(OpenAI 兼容接口)。

    使用 OpenAI 兼容的 /v1/chat/completions 端点。
    支持 deepseek-v4-flash 和 deepseek-v4-pro 模型。
    """

    def __init__(self, cfg: Optional[Config] = None) -> None:
        self._cfg = cfg or config
        self._client: Any = None

    @property
    def _openai(self) -> Any:
        """延迟初始化 OpenAI 客户端。"""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "需要 openai 库: pip install openai"
                ) from None

            self._client = OpenAI(
                api_key=self._cfg.api_key,
                base_url=self._cfg.base_url,
                timeout=self._cfg.api_timeout_seconds,
            )
        return self._client

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        model = model or self._cfg.default_model
        kwargs: dict[str, Any] = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format

        for attempt in range(self._cfg.api_max_retries + 1):
            try:
                resp = self._openai.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content
                return content or ""
            except Exception as e:
                logger.warning(
                    "DeepSeek API 调用失败 (attempt %d/%d): %s",
                    attempt + 1,
                    self._cfg.api_max_retries + 1,
                    e,
                )
                if attempt >= self._cfg.api_max_retries:
                    raise RuntimeError(
                        f"DeepSeek API 调用在 {self._cfg.api_max_retries + 1} 次重试后仍失败"
                    ) from e

        return ""

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        response_format = {"type": "json_object"}
        text = self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON
            import re

            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                return json.loads(m.group(0))
            raise ValueError(f"模型返回了非法的 JSON: {text[:500]}")


class MockProvider(ModelProvider):
    """模拟提供者,用于测试和开发(无 API 调用)。

    基于规则返回预定义的分析结果,不消耗 API 配额。
    """

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        return json.dumps({"mock": True, "note": "MockProvider - no real API call"})

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        return {"mock": True, "note": "MockProvider - no real API call"}


def create_provider(
    provider: str = "deepseek",
    cfg: Optional[Config] = None,
) -> ModelProvider:
    """工厂函数:根据名称创建模型提供者。

    Args:
        provider: "deepseek" | "mock"
        cfg: 配置对象,None 使用全局配置

    Returns:
        ModelProvider 实例
    """
    cfg = cfg or config
    if provider == "mock":
        return MockProvider()
    if provider == "deepseek":
        return DeepSeekProvider(cfg)
    raise ValueError(f"不支持的 provider: {provider}")

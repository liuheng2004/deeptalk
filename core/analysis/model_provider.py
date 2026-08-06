# -*- coding: utf-8 -*-
"""模型接入抽象层。"""

from __future__ import absolute_import

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .config import Config, config

logger = logging.getLogger(__name__)


class ModelProvider(ABC):
    @abstractmethod
    def chat(self, messages, model=None, temperature=0.3, max_tokens=2048, response_format=None):
        pass

    @abstractmethod
    def chat_json(self, messages, model=None, temperature=0.3, max_tokens=2048):
        pass


class DeepSeekProvider(ModelProvider):
    def __init__(self, cfg=None):
        self._cfg = cfg or config
        self._client = None

    @property
    def _openai(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("需要 openai 库: pip install openai")
            self._client = OpenAI(
                api_key=self._cfg.api_key,
                base_url=self._cfg.base_url,
                timeout=self._cfg.api_timeout_seconds,
            )
        return self._client

    def chat(self, messages, model=None, temperature=0.3, max_tokens=2048, response_format=None):
        model = model or self._cfg.default_model
        kwargs = dict(model=model, messages=messages,
                      temperature=temperature, max_tokens=max_tokens)
        if response_format:
            kwargs["response_format"] = response_format
        for attempt in range(self._cfg.api_max_retries + 1):
            try:
                resp = self._openai.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except Exception as e:
                logger.warning("DeepSeek API err (attempt %d/%d): %s",
                               attempt + 1, self._cfg.api_max_retries + 1, e)
                if attempt >= self._cfg.api_max_retries:
                    raise RuntimeError(
                        "API call failed after {} retries".format(
                            self._cfg.api_max_retries + 1))
        return ""

    def chat_json(self, messages, model=None, temperature=0.3, max_tokens=2048):
        text = self.chat(messages, model=model, temperature=temperature,
                         max_tokens=max_tokens, response_format={"type": "json_object"})
        try:
            return json.loads(text)
        except ValueError:
            import re
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                return json.loads(m.group(0))
            raise ValueError("Model returned invalid JSON: {}".format(text[:500]))


class MockProvider(ModelProvider):
    def chat(self, messages, model=None, temperature=0.3, max_tokens=2048, response_format=None):
        return json.dumps({"mock": True})

    def chat_json(self, messages, model=None, temperature=0.3, max_tokens=2048):
        return {"mock": True, "note": "MockProvider"}


def create_provider(provider="deepseek", cfg=None):
    cfg = cfg or config
    if provider == "mock":
        return MockProvider()
    if provider == "deepseek":
        return DeepSeekProvider(cfg)
    raise ValueError("不支持的 provider: {}".format(provider))

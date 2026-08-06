# -*- coding: utf-8 -*-
"""DeepSeek / OpenAI 兼容模型提供者抽象。

优先使用 openai 库;不可用时(如 Python 3.5 环境)回退到纯标准库
HTTP 客户端,保证 API 路径可用。
"""
from __future__ import absolute_import, unicode_literals

import json
import logging
import urllib.request
import urllib.error

from .config import Config, config

logger = logging.getLogger(__name__)


def _openai_usable():
    """openai 库在本环境是否可用(导入子模块需无语法/导入错误)。"""
    try:
        from openai import OpenAI  # noqa
        return True
    except Exception:
        return False


class ModelProvider(object):
    def chat(self, messages, model=None, temperature=0.3, max_tokens=2048,
             response_format=None):
        raise NotImplementedError

    def chat_json(self, messages, model=None, temperature=0.3, max_tokens=2048):
        text = self.chat(messages, model=model, temperature=temperature,
                         max_tokens=max_tokens,
                         response_format={"type": "json_object"})
        try:
            return json.loads(text)
        except ValueError:
            import re
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                return json.loads(m.group(0))
            raise ValueError("Model returned invalid JSON: " + text[:500])


class DeepSeekProvider(ModelProvider):
    """DeepSeek(OpenAI 兼容)提供者。openai 库不可用时走标准库 HTTP。"""

    def __init__(self, cfg=None):
        self._cfg = cfg or config
        self._client = None
        self._use_openai = _openai_usable()

    def _openai(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self._cfg.api_key,
                base_url=self._cfg.base_url,
                timeout=self._cfg.api_timeout_seconds,
            )
        return self._client

    def _chat_stdlib(self, messages, model, temperature, max_tokens,
                     response_format):
        base = (self._cfg.base_url or "https://api.deepseek.com").rstrip("/")
        url = base + "/chat/completions"
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            body["response_format"] = response_format
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self._cfg.api_key,
            })
        with urllib.request.urlopen(req,
                                    timeout=self._cfg.api_timeout_seconds) as r:
            resp = json.loads(r.read().decode("utf-8"))
        return resp["choices"][0]["message"]["content"] or ""

    def chat(self, messages, model=None, temperature=0.3, max_tokens=2048,
             response_format=None):
        model = model or self._cfg.default_model
        for attempt in range(self._cfg.api_max_retries + 1):
            try:
                if self._use_openai:
                    resp = self._openai().chat.completions.create(
                        model=model, messages=messages,
                        temperature=temperature, max_tokens=max_tokens,
                        **({"response_format": response_format}
                           if response_format else {}))
                    return resp.choices[0].message.content or ""
                return self._chat_stdlib(
                    messages, model, temperature, max_tokens, response_format)
            except Exception as e:
                logger.warning("DeepSeek API err (attempt %d/%d): %s",
                               attempt + 1, self._cfg.api_max_retries + 1, e)
                if attempt >= self._cfg.api_max_retries:
                    raise RuntimeError(
                        "API call failed after {} retries".format(
                            self._cfg.api_max_retries + 1))
        return ""


class MockProvider(ModelProvider):
    """离线 mock:按规则返回确定性结果,便于测试与演示。"""

    def __init__(self, cfg=None):
        self._cfg = cfg or config

    def chat(self, messages, model=None, temperature=0.3, max_tokens=2048,
             response_format=None):
        return json.dumps({
            "mock": True,
            "depth_score": 55.0,
            "dimensions": {"emotion": 50.0, "event": 55.0,
                           "continuity": 50.0, "interaction": 50.0},
            "summary": "一段值得记录的对话。",
            "tags": ["深度对话"],
            "golden_quotes": [],
        })

    def chat_json(self, messages, model=None, temperature=0.3, max_tokens=2048):
        return json.loads(self.chat(messages, model=model))


def create_provider(provider="deepseek", cfg=None):
    cfg = cfg or config
    if provider == "deepseek":
        return DeepSeekProvider(cfg)
    if provider == "mock":
        return MockProvider(cfg)
    raise ValueError("unknown provider: " + provider)

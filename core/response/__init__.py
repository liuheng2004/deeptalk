# -*- coding: utf-8 -*-
"""第三方回应生成。

基于识别结果生成有温度的第三方视角回应。优先调用 DeepSeek;
无 API Key 或调用失败时使用本地模板,保证演示离线可用。
"""
from __future__ import absolute_import

from .engine import generate_response, generate_response_with_api

__all__ = ["generate_response", "generate_response_with_api"]

# -*- coding: utf-8 -*-
"""记忆卡片生成。

卡片数据模型由识别结果构建;PNG 渲染由 scripts/render 的
Node 渲染器完成(见 core.export.renderer)。
"""
from __future__ import absolute_import

from .model import Card, build_card

__all__ = ["Card", "build_card"]

# -*- coding: utf-8 -*-
"""微信 txt 导入解析。

将微信官方「邮件发送聊天记录」导出的 txt 解析为符合
docs/contracts/session.schema.json 的 ChatSession 模型。

实现依据:docs/guides/parser-spec.md。
"""
from __future__ import absolute_import

from .wechat import Message, ChatSession, parse_wechat_file, parse_wechat_text

__all__ = ["Message", "ChatSession", "parse_wechat_file", "parse_wechat_text"]

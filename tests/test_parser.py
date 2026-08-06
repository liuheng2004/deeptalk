# -*- coding: utf-8 -*-
"""解析器单元/集成测试。"""
from __future__ import absolute_import, unicode_literals

import os
import unittest

from core.parser import parse_wechat_file, parse_wechat_text

SAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "guides", "wechat-export-samples")


class ParserBasicTest(unittest.TestCase):
    def test_sample01_basic_daily(self):
        s = parse_wechat_file(os.path.join(SAMPLES, "sample-01-basic-daily.txt"))
        self.assertEqual(s.peer, "星河")
        self.assertEqual(s.message_count, 9)
        self.assertEqual(s.created_at, "2024-03-15T09:30:00+08:00")
        self.assertEqual(s.updated_at, "2024-03-15T10:15:00+08:00")
        self.assertEqual(s.source, "wechat-email-txt")
        self.assertEqual(len(s.messages), 9)
        # 消息类型与发送者
        self.assertEqual(s.messages[0].sender, "星河")
        self.assertEqual(s.messages[1].sender, "me")
        self.assertEqual(s.messages[2].sender, "星河")
        self.assertEqual(s.messages[7].type, "system")
        self.assertEqual(s.messages[7].sender, "星河")
        self.assertTrue(s.messages[7].inferred_time)
        # session_id 长度
        self.assertEqual(len(s.session_id), 17)

    def test_sample02_rich_features(self):
        s = parse_wechat_file(os.path.join(SAMPLES, "sample-02-rich-features.txt"))
        self.assertEqual(s.peer, "晨曦")
        self.assertEqual(s.message_count, 11)
        # voip_text
        voip = s.messages[3]
        self.assertEqual(voip.type, "voip_text")
        self.assertIn("恭喜你呀", voip.content)
        # quote + quote_of
        quote = s.messages[4]
        self.assertEqual(quote.type, "quote")
        self.assertEqual(quote.quote_of, "m3")
        # system 拍一拍
        self.assertEqual(s.messages[6].type, "system")
        self.assertIn("拍了拍", s.messages[6].content)
        # 时间戳推断
        self.assertTrue(s.messages[2].inferred_time)

    def test_sample03_multiline(self):
        s = parse_wechat_file(os.path.join(SAMPLES, "sample-03-multiline-edge.txt"))
        self.assertEqual(s.peer, "远舟")
        self.assertEqual(s.message_count, 10)
        self.assertEqual(s.messages[0].content,
                         "你最近怎么样\n好久没联系了")
        self.assertEqual(s.messages[0].sender, "远舟")
        self.assertEqual(s.messages[1].sender, "me")
        self.assertEqual(s.messages[7].type, "system")
        self.assertEqual(len(s.messages[0].timestamp), 25)

    def test_empty_text(self):
        s = parse_wechat_text("")
        self.assertEqual(s.message_count, 0)
        self.assertEqual(s.messages, [])

    def test_bom_and_crlf(self):
        text = "\ufeff消息记录\r\n\r\n消息发起人:阿明\r\n聊天对象:小美\r\n\r\n" \
               "2024-1-2 10:00:00 小美\r\n你好\r\n\r\n" \
               "2024-1-2 10:01:00 阿明\r\n你好呀\r\n"
        s = parse_wechat_text(text)
        self.assertEqual(s.peer, "小美")
        self.assertEqual(s.message_count, 2)
        self.assertEqual(s.messages[0].content, "你好")
        self.assertEqual(s.messages[1].sender, "me")


if __name__ == "__main__":
    unittest.main()

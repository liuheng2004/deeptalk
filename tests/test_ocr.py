# -*- coding: utf-8 -*-
"""AI 聊天截图 OCR 导入单测:用合成截图验证气泡分组与说话人识别。"""
from __future__ import absolute_import, unicode_literals

import os
import tempfile
import unittest

from PIL import Image, ImageDraw

from core.parser.ocr import parse_ai_screenshots


def _make_chat_image(path, left_texts, right_texts):
    """画一张左右气泡聊天截图(白底黑字,气泡为浅灰圆角矩形)。"""
    img = Image.new("RGB", (900, 700), "white")
    d = ImageDraw.Draw(img)
    for texts, side in ((left_texts, "left"), (right_texts, "right")):
        y = 30
        for t in texts:
            if side == "left":
                x0, x1 = 30, 420
            else:
                x0, x1 = 480, 870
            d.rectangle([x0, y, x1, y + 70], fill="#eeeeee")
            d.text((x0 + 20, y + 24), t, fill="black")
            y += 110
    img.save(path)


class OcrPipelineTest(unittest.TestCase):
    def test_synthetic_left_right_bubbles(self):
        tmpdir = tempfile.mkdtemp(prefix="deeptalk-ocr-")
        img1 = os.path.join(tmpdir, "chat1.png")
        _make_chat_image(
            img1,
            left_texts=["hello, this is AI", "sure, let me think"],
            right_texts=["hi AI", "thanks!"],
        )
        session = parse_ai_screenshots([img1], peer="AI")
        self.assertEqual(session["source"], "ai-chat-screenshot")
        self.assertGreaterEqual(session["message_count"], 4)
        senders = [m["sender"] for m in session["messages"]]
        self.assertIn("me", senders)
        self.assertIn("AI", senders)
        for m in session["messages"]:
            self.assertTrue(m["inferred_time"])
            self.assertEqual(m["type"], "text")
            self.assertTrue(m["content"].strip())
        self.assertIn("OCR", session["note"])

    def test_empty_image_raises(self):
        tmpdir = tempfile.mkdtemp(prefix="deeptalk-ocr-")
        blank = os.path.join(tmpdir, "blank.png")
        Image.new("RGB", (600, 400), "white").save(blank)
        with self.assertRaises(ValueError):
            parse_ai_screenshots([blank])


if __name__ == "__main__":
    unittest.main()

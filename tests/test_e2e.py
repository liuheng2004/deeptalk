# -*- coding: utf-8 -*-
"""全链路 E2E 集成测试:导入 -> 识别 -> 卡片 -> 回应 -> 导出。"""
from __future__ import absolute_import, unicode_literals

import os
import struct
import tempfile
import unittest

from core.analysis import create_engine
from core.card.model import build_card
from core.pipeline import run_pipeline
from core.parser import parse_wechat_file

SAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "guides", "wechat-export-samples")


class AnalysisTest(unittest.TestCase):
    def test_analyze_result_shape(self):
        s = parse_wechat_file(os.path.join(SAMPLES, "sample-02-rich-features.txt"))
        engine = create_engine(provider="mock")
        results = engine.analyze_session(s.to_dict())
        self.assertTrue(len(results) >= 1)
        r = results[0]
        self.assertTrue(0.0 <= r.depth_score <= 100.0)
        for k in ("emotion", "event", "continuity", "interaction"):
            self.assertIn(k, r.dimensions)
            self.assertTrue(0.0 <= r.dimensions[k] <= 100.0)
        self.assertEqual(r.session_id, s.session_id)
        self.assertTrue(r.summary)
        self.assertTrue(r.messages)
        self.assertIsNotNone(r.is_deep)

    def test_segments(self):
        s = parse_wechat_file(os.path.join(SAMPLES, "sample-02-rich-features.txt"))
        engine = create_engine(provider="mock")
        results = engine.analyze_session(s.to_dict())
        self.assertTrue(len(results) >= 1)
        for r in results:
            self.assertTrue(len(r.messages) >= 1)

    def test_card_build(self):
        s = parse_wechat_file(os.path.join(SAMPLES, "sample-01-basic-daily.txt"))
        engine = create_engine(provider="mock")
        r = engine.analyze_session(s.to_dict())[0]
        card = build_card(r, s)
        self.assertEqual(card.peer, s.peer)
        self.assertTrue(card.golden_quotes)
        self.assertTrue(card.tags)


class PipelineE2ETest(unittest.TestCase):
    def test_full_pipeline_local(self):
        sample = os.path.join(SAMPLES, "sample-02-rich-features.txt")
        tmp = tempfile.mkdtemp(prefix="deeptalk-e2e-")
        result = run_pipeline(sample, out_dir=tmp, use_api=False)
        # 解析
        self.assertEqual(result.session.peer, "晨曦")
        self.assertTrue(result.session.message_count > 0)
        # 识别
        self.assertIsNotNone(result.analysis.depth_score)
        self.assertIn("depth_score", result.summary_dict())
        # 卡片
        self.assertTrue(result.card)
        self.assertEqual(result.card.peer, "晨曦")
        # 回应
        self.assertTrue(result.response["text"])
        # 导出
        self.assertTrue(os.path.exists(result.exports["markdown"]))
        self.assertTrue(os.path.exists(result.exports["png"]))
        self.assertTrue(os.path.exists(result.exports["pdf"]))
        # PNG 头校验
        with open(result.exports["png"], "rb") as f:
            head = f.read(24)
        self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
        w, h = struct.unpack(">II", head[16:24])
        self.assertEqual((w, h), (1080, 1440))
        # PDF 头校验
        with open(result.exports["pdf"], "rb") as f:
            self.assertTrue(f.read(4).startswith(b"%PDF"))
        # Markdown front matter
        with open(result.exports["markdown"], "r", encoding="utf-8") as f:
            md = f.read()
        self.assertTrue(md.startswith("---"))
        self.assertIn("session_id:", md)


if __name__ == "__main__":
    unittest.main()

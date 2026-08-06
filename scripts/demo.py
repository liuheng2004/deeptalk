# -*- coding: utf-8 -*-
"""端到端演示:跑通 导入->识别->卡片->回应->导出,输出到 demo-out/。"""
from __future__ import absolute_import, unicode_literals

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.pipeline import run_pipeline


def main():
    sample = os.path.join(
        ROOT, "docs", "guides", "wechat-export-samples",
        "sample-02-rich-features.txt")
    out_dir = os.path.join(ROOT, "demo-out")
    print("== DeepTalk E2E Demo ==")
    print("输入:", sample)
    result = run_pipeline(sample, out_dir=out_dir, use_api=False)
    print(json.dumps(result.summary_dict(), ensure_ascii=False, indent=2))
    print("输出目录:", out_dir)
    for k, p in result.exports.items():
        if "error" not in k:
            print(" -", k, os.path.getsize(p), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

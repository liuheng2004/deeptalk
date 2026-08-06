# -*- coding: utf-8 -*-
"""core.analysis CLI 入口。"""

from __future__ import absolute_import, print_function

import argparse
import json
import sys
from pathlib import Path

from . import AnalysisEngine, AnalysisResult, create_engine


def format_result(r):
    return {
        "segment_id": r.segment_id, "session_id": r.session_id,
        "depth_score": r.depth_score, "threshold": r.threshold,
        "is_deep": r.is_deep, "dimensions": r.dimensions,
        "start_time": r.start_time, "end_time": r.end_time,
        "duration_minutes": r.duration_minutes, "summary": r.summary,
        "tags": r.tags, "golden_quotes": r.golden_quotes,
        "messages": r.messages, "model": r.model,
    }


def main():
    parser = argparse.ArgumentParser(description="DeepTalk 深度对话识别引擎")
    parser.add_argument("input", type=str, help="会话 JSON 文件路径")
    parser.add_argument("--model", type=str, default=None,
                        help="模型名称(默认从 .env 读取)")
    parser.add_argument("--threshold", type=float, default=60.0,
                        help="深度判定阈值(0-100)")
    parser.add_argument("--provider", type=str, default="deepseek",
                        choices=["deepseek", "mock"])
    parser.add_argument("--output", type=str, default=None,
                        help="输出 JSON 文件路径(默认 stdout)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print("错误: 文件不存在: {}".format(args.input), file=sys.stderr)
        sys.exit(1)

    with open(str(input_path), "r", encoding="utf-8") as f:
        session = json.load(f)

    engine = create_engine(provider=args.provider)
    results = engine.analyze_session(session, model=args.model)
    output = [format_result(r) for r in results]

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print("分析完成,{} 个片段写入 {}".format(len(output), args.output))
    else:
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        print()


if __name__ == "__main__":
    main()

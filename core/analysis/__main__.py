"""
core.analysis CLI 入口。

用法:
    python -m core.analysis <session.json> [--model deepseek-v4-pro] [--threshold 60]

从符合 session.schema.json 的 JSON 文件读取会话,
输出符合 analysis-result.schema.json 的分析结果。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import AnalysisEngine, AnalysisResult, create_engine


def format_result(r: AnalysisResult) -> dict:
    """将 AnalysisResult 转为 schema 兼容的字典。"""
    return {
        "segment_id": r.segment_id,
        "session_id": r.session_id,
        "depth_score": r.depth_score,
        "threshold": r.threshold,
        "is_deep": r.is_deep,
        "dimensions": r.dimensions,
        "start_time": r.start_time,
        "end_time": r.end_time,
        "duration_minutes": r.duration_minutes,
        "summary": r.summary,
        "tags": r.tags,
        "golden_quotes": r.golden_quotes,
        "messages": r.messages,
        "model": r.model,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DeepTalk 深度对话识别引擎",
    )
    parser.add_argument(
        "input",
        type=str,
        help="会话 JSON 文件路径(符合 session.schema.json)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="模型名称(默认从 .env 读取: deepseek-v4-flash)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=60.0,
        help="深度判定阈值(0-100, 默认 60)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="deepseek",
        choices=["deepseek", "mock"],
        help="模型提供者(默认 deepseek)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出 JSON 文件路径(默认 stdout)",
    )

    args = parser.parse_args()

    # 读取输入
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        session = json.load(f)

    # 创建引擎并分析
    engine = create_engine(provider=args.provider)
    results = engine.analyze_session(session, model=args.model)

    # 格式化输出
    output = [format_result(r) for r in results]

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"分析完成,{len(output)} 个片段写入 {args.output}")
    else:
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        print()


if __name__ == "__main__":
    main()

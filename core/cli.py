# -*- coding: utf-8 -*-
"""DeepTalk core 命令行入口。"""
from __future__ import absolute_import, unicode_literals

import argparse
import json
import sys

from .analysis.engine import analyze_session, analyze_session_with_api
from .analysis.config import config
from .parser import parse_wechat_file
from .pipeline import run_pipeline


def _cmd_parse(args):
    session = parse_wechat_file(args.file, me_nickname=args.me)
    print(json.dumps(session.to_dict(), ensure_ascii=False, indent=2))


def _cmd_analyze(args):
    session = parse_wechat_file(args.file, me_nickname=args.me)
    if args.api:
        result = analyze_session_with_api(session)
    else:
        result = analyze_session(session)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


def _cmd_run(args):
    use_api = None if args.api is None else bool(args.api)
    result = run_pipeline(args.file, out_dir=args.outdir,
                          use_api=use_api, me_nickname=args.me)
    print(json.dumps(result.summary_dict(), ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="deeptalk-core",
                                     description="DeepTalk 核心链路")
    sub = parser.add_subparsers(dest="command")

    p_parse = sub.add_parser("parse", help="解析微信 txt -> ChatSession JSON")
    p_parse.add_argument("file")
    p_parse.add_argument("--me", default=None)
    p_parse.set_defaults(func=_cmd_parse)

    p_ana = sub.add_parser("analyze", help="识别 -> analysis-result JSON")
    p_ana.add_argument("file")
    p_ana.add_argument("--me", default=None)
    p_ana.add_argument("--api", action="store_true")
    p_ana.set_defaults(func=_cmd_analyze)

    p_run = sub.add_parser(
        "run", help="全链路:导入->识别->卡片->回应->导出")
    p_run.add_argument("file")
    p_run.add_argument("--outdir", default="out")
    p_run.add_argument("--me", default=None)
    p_run.add_argument("--api", action="store_true",
                       help="强制走 DeepSeek API")
    p_run.add_argument("--local", action="store_true",
                       help="强制走本地规则(离线)")
    p_run.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    if getattr(args, "local", False):
        args.api = False
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

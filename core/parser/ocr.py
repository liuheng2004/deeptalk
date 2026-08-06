# -*- coding: utf-8 -*-
"""AI 聊天截图导入:图片 -> OCR -> 会话模型(session.schema.json)。

使用本地 RapidOCR(onnxruntime),离线运行,数据不出设备。
适配豆包 / ChatGPT / DeepSeek 等"左右气泡"布局的聊天截图。

约定:
- 默认右侧气泡 = 本机用户(me),左侧 = AI;可用 --me-side 切换;
- 截图通常没有时间戳,messages.timestamp 按顺序推断并标注 inferred_time=True;
- 只提取文本,不保存原图(与 v1.6 决策一致)。

用法:
    python -m core.parser.ocr chat1.png chat2.png --peer AI --me-side right
"""

from __future__ import absolute_import, unicode_literals

import argparse
import hashlib
import json
import os
import sys
import time


def _get_engine():
    """懒加载 RapidOCR 引擎(避免依赖缺失时影响其他模块导入)。"""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError(
            "RapidOCR 未安装,请先执行: .venv/Scripts/pip install rapidocr_onnxruntime"
        ) from exc
    return RapidOCR()


def ocr_image(path):
    """识别单张图片,返回行列表:[{text, box, score}]。"""
    engine = _get_engine()
    result, _ = engine(str(path))
    if not result:
        return []
    lines = []
    for box, text, score in result:
        lines.append({
            "text": str(text),
            "box": [[float(p[0]), float(p[1])] for p in box],
            "score": float(score),
        })
    return lines


def _line_center(line):
    xs = [p[0] for p in line["box"]]
    ys = [p[1] for p in line["box"]]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _line_height(line):
    ys = [p[1] for p in line["box"]]
    return max(ys) - min(ys)


def _cluster_bubbles(lines, gap_ratio=1.5):
    """把 OCR 行按纵向邻近聚合成气泡(消息)。"""
    if not lines:
        return []
    ordered = sorted(lines, key=lambda ln: _line_center(ln)[1])
    bubbles = []
    for line in ordered:
        if not bubbles:
            bubbles.append([line])
            continue
        cur = bubbles[-1]
        heights = [_line_height(ln) for ln in cur]
        med_h = sorted(heights)[len(heights) // 2] or 10.0
        prev_bottom = max(_line_center(ln)[1] + _line_height(ln) / 2 for ln in cur)
        cur_top = _line_center(line)[1] - _line_height(line) / 2
        gap = cur_top - prev_bottom
        prev_xs = [p[0] for ln in cur for p in ln["box"]]
        line_xs = [p[0] for p in line["box"]]
        overlap = (min(prev_xs) <= max(line_xs)) and (max(prev_xs) >= min(line_xs))
        if gap <= med_h * gap_ratio and overlap:
            cur.append(line)
        else:
            bubbles.append([line])
    return bubbles


def _bubble_text(bubble):
    return "".join(ln["text"] for ln in sorted(bubble, key=lambda ln: _line_center(ln)[1]))


def _bubble_side(bubble, img_width, me_side):
    """按气泡 x 中心判断说话人。"""
    xs = [p[0] for ln in bubble for p in ln["box"]]
    cx = (min(xs) + max(xs)) / 2.0
    is_right = cx > img_width / 2.0
    if me_side == "right":
        return "me" if is_right else "peer"
    return "peer" if is_right else "me"


def _image_size(path):
    from PIL import Image
    with Image.open(str(path)) as img:
        return img.width, img.height


def parse_ai_screenshots(image_paths, peer="AI", me_side="right",
                         source="ai-chat-screenshot"):
    """多张截图 -> 会话模型 dict(符合 session.schema.json)。"""
    messages = []
    day = time.strftime("%Y-%m-%d")
    seq = 0
    for img in image_paths:
        width, _ = _image_size(img)
        lines = ocr_image(img)
        for bubble in _cluster_bubbles(lines):
            text = _bubble_text(bubble)
            if not text.strip():
                continue
            sender = _bubble_side(bubble, width, me_side)
            seq += 1
            hh = 8 + seq // 3600
            mm = (seq % 3600) // 60
            ss = seq % 60
            messages.append({
                "id": "img_%s_%04d" % (hashlib.md5(str(img).encode("utf-8")).hexdigest()[:6], seq),
                "sender": "me" if sender == "me" else peer,
                "content": text,
                "type": "text",
                "timestamp": "%sT%02d:%02d:%02d+08:00" % (day, hh, mm, ss),
                "inferred_time": True,
            })

    if not messages:
        raise ValueError("未从图片中识别出任何文本,请确认截图清晰且为聊天界面")

    peer_label = "我" if peer == "me" else peer
    session_id = "img-" + hashlib.sha1(
        (peer_label + messages[0]["content"][:20]).encode("utf-8")
    ).hexdigest()[:12]
    return {
        "session_id": session_id,
        "peer": peer_label,
        "created_at": messages[0]["timestamp"],
        "updated_at": messages[-1]["timestamp"],
        "source": source,
        "message_count": len(messages),
        "messages": messages,
        "note": "由聊天截图经本地 OCR 导入;时间戳按顺序推断,原图未保存。",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI 聊天截图 -> 会话模型 JSON")
    parser.add_argument("images", nargs="+", help="聊天截图路径(按对话顺序)")
    parser.add_argument("--peer", default="AI", help="AI 方昵称(默认 AI)")
    parser.add_argument("--me-side", choices=["left", "right"], default="right",
                        help="本机用户气泡在哪一侧(默认 right)")
    parser.add_argument("--out", default=None, help="输出 JSON 文件路径")
    args = parser.parse_args(argv)

    session = parse_ai_screenshots(args.images, peer=args.peer, me_side=args.me_side)
    text = json.dumps(session, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        sys.stderr.write("written: %s\n" % args.out)
    else:
        print(text)


if __name__ == "__main__":
    main()

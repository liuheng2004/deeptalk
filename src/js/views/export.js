// 导出面板 —— 按 docs/contracts/export-template.md:图片(PNG)/ PDF / Markdown(MD)。
// 字段来自 analysis-result.schema.json + session.schema.json。
//   - PNG:canvas 实时绘制 1080×1440 分享卡,可下载(离线可用)。
//   - MD :合成带 YAML front matter 的 Markdown,可下载。
//   - PDF:调用浏览器打印(可「另存为 PDF」)。
//   - 水印:默认开;隐私:默认隐藏昵称/评分,可手动开启。
import { getSession, getAnalysis } from "../store.js";
import { computeMood } from "../data.js";
import { escapeHtml, formatDateTime, fromNow } from "../util.js";

export function mount(root, params) {
  const a = getAnalysis(params.seg);
  if (!a) {
    root.innerHTML = `<div class="empty">未找到该片段。<a href="#/">返回卡片流</a></div>`;
    return;
  }
  const session = getSession();
  const mood = computeMood(a);

  const opts = { format: "png", watermark: true, showSensitive: false };

  root.innerHTML = `
    <section class="page-head">
      <h1>导出面板</h1>
      <p>会话:<b>${escapeHtml(session.peer)}</b> · 片段 ${escapeHtml(a.segment_id)}</p>
    </section>

    <div class="panel">
      <h3 style="margin-top:0">导出格式</h3>
      <div class="export-options" id="fmts">
        <div class="fmt selected" data-fmt="png"><h4>图片 PNG</h4><p>1080×1440 朋友圈分享卡</p></div>
        <div class="fmt" data-fmt="pdf"><h4>PDF</h4><p>A4 存档文档</p></div>
        <div class="fmt" data-fmt="md"><h4>Markdown</h4><p>可迁移笔记(Obsidian)</p></div>
      </div>

      <div style="margin-top:16px">
        <div class="toggle-row">
          <label class="switch"><input type="checkbox" id="wm" checked><span class="slot"></span></label>
          <span>DeepTalk 水印</span>
        </div>
        <div class="toggle-row">
          <label class="switch"><input type="checkbox" id="sens"><span class="slot"></span></label>
          <span>显示昵称 / 深度评分(默认隐藏)</span>
        </div>
      </div>

      <div class="btn-row" style="margin-top:16px">
        <button class="btn" id="doExport">导出</button>
        <a class="btn secondary" href="#/detail/${escapeHtml(a.segment_id)}">← 返回详情</a>
      </div>
    </div>

    <h3 style="margin-top:18px">预览</h3>
    <div class="export-preview"><canvas id="cv" width="1080" height="1440"></canvas></div>

    <!-- 打印用(PDF) -->
    <div id="printArea" style="display:none"></div>`;

  const cv = root.querySelector("#cv");
  const ctx = cv.getContext("2d");

  function draw() {
    const W = 1080, H = 1440;
    const high = a.depth_score >= 70;
    const g = ctx.createLinearGradient(0, 0, 0, H);
    if (high) { g.addColorStop(0, "#3a2a4d"); g.addColorStop(1, "#1a1326"); }
    else { g.addColorStop(0, "#2a2f3d"); g.addColorStop(1, "#161922"); }
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

    const pad = 90;
    ctx.textBaseline = "top";
    // 顶部:日期 + 距今
    ctx.fillStyle = "rgba(232,237,255,0.75)";
    ctx.font = "34px -apple-system, 'PingFang SC', sans-serif";
    ctx.fillText(formatDateTime(a.start_time).split(" ")[0], pad, 90);
    ctx.fillStyle = "rgba(232,237,255,0.5)";
    ctx.font = "28px sans-serif";
    ctx.fillText(fromNow(a.start_time), pad, 140);

    // 标签
    let ty = 220;
    ctx.fillStyle = "rgba(255,200,140,0.9)";
    ctx.font = "34px 'PingFang SC', sans-serif";
    (a.tags || []).forEach((t) => { ctx.fillText("#" + t, pad, ty); ty += 48; });

    // 金句(大字)
    ctx.fillStyle = "#f3f6ff";
    const quotes = (a.golden_quotes || []).slice(0, 2);
    let qy = 380;
    quotes.forEach((q) => {
      wrapText(ctx, "“" + q.text + "”", pad, qy, W - pad * 2, 70, "bold 52px 'PingFang SC', sans-serif");
      qy += 220;
    });

    // 底部:对方昵称、深度评分、水印
    const baseY = H - 200;
    if (opts.showSensitive) {
      ctx.fillStyle = "#e8edff";
      ctx.font = "40px 'PingFang SC', sans-serif";
      ctx.fillText(escapeHtml(session.peer), pad, baseY);
      ctx.fillStyle = "#ffd9a8";
      ctx.font = "bold 44px sans-serif";
      ctx.fillText("深度 " + Math.round(a.depth_score), pad, baseY + 60);
    } else {
      ctx.fillStyle = "rgba(232,237,255,0.5)";
      ctx.font = "34px 'PingFang SC', sans-serif";
      ctx.fillText("（已隐藏昵称 / 评分）", pad, baseY + 20);
    }

    if (opts.watermark) {
      ctx.fillStyle = "rgba(232,237,255,0.4)";
      ctx.font = "30px sans-serif";
      ctx.textAlign = "right";
      ctx.fillText("DeepTalk", W - pad, H - 70);
      ctx.textAlign = "left";
    }
  }

  function wrapText(c, text, x, y, maxW, lh, font) {
    c.font = font; c.fillStyle = "#f3f6ff";
    let line = "", yy = y;
    for (const ch of text) {
      if (c.measureText(line + ch).width > maxW && line) { c.fillText(line, x, yy); line = ch; yy += lh; }
      else line += ch;
    }
    if (line) c.fillText(line, x, yy);
  }

  function redraw() { draw(); }

  root.querySelectorAll(".fmt").forEach((el) => {
    el.addEventListener("click", () => {
      root.querySelectorAll(".fmt").forEach((x) => x.classList.remove("selected"));
      el.classList.add("selected");
      opts.format = el.dataset.fmt;
    });
  });
  root.querySelector("#wm").addEventListener("change", (e) => { opts.watermark = e.target.checked; redraw(); });
  root.querySelector("#sens").addEventListener("change", (e) => { opts.showSensitive = e.target.checked; redraw(); });

  root.querySelector("#doExport").addEventListener("click", () => {
    if (opts.format === "png") {
      cv.toBlob((blob) => downloadBlob(blob, `deeptalk-${a.segment_id}.png`));
    } else if (opts.format === "md") {
      downloadBlob(new Blob([buildMarkdown(a, session, opts)], { type: "text/markdown" }), `deeptalk-${a.segment_id}.md`);
    } else {
      // PDF:用打印对话框(可另存为 PDF)
      const pa = root.querySelector("#printArea");
      pa.innerHTML = `<img src="${cv.toDataURL("image/png")}" style="width:100%" />`;
      pa.style.display = "block";
      window.print();
      pa.style.display = "none";
    }
  });

  redraw();
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function buildMarkdown(a, session, opts) {
  const title = a.tags?.length ? a.tags[0] : "深度对话";
  const front = `---
title: ${title}
date: ${a.start_time.slice(0, 10)}
peer: ${opts.showSensitive ? session.peer : "（已隐藏）"}
depth_score: ${Math.round(a.depth_score)}
tags: [${a.tags?.join(", ") || ""}]
session_id: ${a.session_id}
segment_id: ${a.segment_id}
---
`;
  const quotes = (a.golden_quotes || []).map((q) => `> ${q.text}`).join("\n\n");
  return `${front}
# ${title}

## 摘要
${a.summary}

## 金句
${quotes || "（无）"}

## 完整对话
${(a.messages || []).map((m) => `- ${m.sender === "me" ? "我" : session.peer}（${m.timestamp.slice(11, 16)}）: ${m.content}`).join("\n")}
`;
}

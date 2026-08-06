// 对话详情页 —— 展示单个 DeepTalkAnalysisResult 的全部契约字段,
// 内嵌「完整剪影版影子回放」。字段与 analysis-result.schema.json 一一对应。
import { getSession, getAnalysis } from "../store.js";
import { computeMood, MOOD_LABEL } from "../data.js";
import { setMood } from "../motion.js";
import { mountShadowReplay } from "../shadow.js";
import { escapeHtml, formatDateTime, formatTime, dimensionsHtml, animateDims, fromNow } from "../util.js";
import { MESSAGE_TYPE_LABEL } from "../contracts.js";

export function mount(root, params) {
  const a = getAnalysis(params.seg);
  if (!a) {
    root.innerHTML = `<div class="empty">未找到该片段。<a href="#/">返回卡片流</a></div>`;
    return;
  }
  const session = getSession();
  const mood = computeMood(a);
  setMood(mood); // 进入详情即呈现该对话的双态氛围

  const quotes = (a.golden_quotes || []).map((q) =>
    `<div class="golden">“${escapeHtml(q.text)}”</div>`).join("");

  const msgs = a.messages.map((m) => {
    const side = m.sender === "me" ? "me" : "peer";
    const who = m.sender === "me" ? "我" : escapeHtml(m.sender);
    const typeCls = m.type === "quote" ? " quote" : (m.type === "system" ? " system" : "");
    const typeTag = MESSAGE_TYPE_LABEL[m.type] ? `<span class="muted small">· ${MESSAGE_TYPE_LABEL[m.type]}</span>` : "";
    const inferred = m.inferred_time ? `<span class="muted small"> · 推断时间</span>` : "";
    return `<div class="msg ${side}${typeCls}">
      <span class="who">${who}${typeTag}</span>
      ${escapeHtml(m.content)}
      <span class="when">${formatTime(m.timestamp)}${inferred}</span>
    </div>`;
  }).join("");

  root.innerHTML = `
    <section class="page-head">
      <h1>${escapeHtml(session.peer)} · 对话片段</h1>
      <p>
        <span class="mood-chip">${MOOD_LABEL[mood]}态</span>
        ${a.is_deep ? `<span class="mood-chip">深度对话</span>` : `<span class="muted small">未达阈值</span>`}
        <span class="muted small">· 片段 ${escapeHtml(a.segment_id)}</span>
      </p>
    </section>

    <div class="panel" style="margin-bottom:18px">
      <div class="row" style="display:flex;gap:18px;align-items:center">
        <div class="score" style="--val:${Math.round(a.depth_score)}"><b>${Math.round(a.depth_score)}</b><small>深度评分</small></div>
        <div>
          <div>阈值 ${Math.round(a.threshold ?? 0)} · 模型 ${escapeHtml(a.model || "—")}</div>
          <div class="muted small">${formatDateTime(a.start_time)} → ${formatDateTime(a.end_time)} · 约 ${Math.round(a.duration_minutes)} 分钟 · ${fromNow(a.start_time)}</div>
        </div>
      </div>
      ${dimensionsHtml(a.dimensions)}
      <p style="margin:14px 0 6px">${escapeHtml(a.summary)}</p>
      <div>${(a.tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>
    </div>

    <h3>完整剪影版影子回放</h3>
    <div id="replay"></div>

    <h3 style="margin-top:18px">金句</h3>
    ${quotes || '<p class="muted">无</p>'}

    <h3 style="margin-top:18px">完整对话(${a.messages.length} 条)</h3>
    <div class="message-list">${msgs}</div>

    <div class="btn-row" style="margin-top:20px">
      <button class="btn" id="toResp">看 AI 回应 →</button>
      <button class="btn secondary" id="toExport">导出此片段 →</button>
      <a class="btn secondary" href="#/">← 返回卡片流</a>
    </div>`;

  animateDims(root);

  // 挂载影子回放(数据驱动:节奏由 a.messages 时间戳间隔决定)
  const replayHost = root.querySelector("#replay");
  const replay = mountShadowReplay(replayHost, {
    messages: a.messages,
    mood,
    reduced: document.documentElement.classList.contains("reduced"),
  });
  root.querySelector("#toResp").addEventListener("click", () => location.hash = `#/response/${a.segment_id}`);
  root.querySelector("#toExport").addEventListener("click", () => location.hash = `#/export/${a.segment_id}`);

  // 清理:停止动画 + 复位全局氛围
  return () => { replay.destroy(); setMood("calm"); };
}

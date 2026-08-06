// 回应页 —— 内置 AI Agent 的第三方视角回应(README 功能)。
// 此处用契约字段(summary / golden_quotes / dimensions)合成演示文案;
// 真实生成由 core/analysis + 模型接入层负责。字段仍来自 analysis-result.schema.json。
import { getSession, getAnalysis } from "../store.js";
import { escapeHtml, formatDateTime } from "../util.js";

const PERSONAS = {
  friend: { name: "知心好友", lead: "作为你的朋友,我想说——" },
  observer: { name: "旁观者", lead: "跳出这段对话来看——" },
  elder: { name: "过来人", lead: "我也曾站在你这个位置——" },
};

function buildReply(a, personaKey) {
  const p = PERSONAS[personaKey] || PERSONAS.friend;
  const quotes = (a.golden_quotes || []).map((q) => `“${q.text}”`).join("、");
  const d = a.dimensions;
  return `${p.lead}
读了你们在 ${formatDateTime(a.start_time)} 的这段对话,我的感受是:${escapeHtml(a.summary)}
最打动我的是那几句——${quotes}。
从维度看,情感深度 ${Math.round(d.emotion)}、互动质量 ${Math.round(d.interaction)},说明你们之间有着真实的在意。
无论接下来怎么选,被接住过的那一刻,已经说明你并不孤单。`;
}

export function mount(root, params) {
  const a = getAnalysis(params.seg);
  if (!a) {
    root.innerHTML = `<div class="empty">未找到该片段。<a href="#/">返回卡片流</a></div>`;
    return;
  }
  const session = getSession();

  root.innerHTML = `
    <section class="page-head">
      <h1>AI 第三方回应</h1>
      <p>会话:<b>${escapeHtml(session.peer)}</b> · 片段 ${escapeHtml(a.segment_id)} · 深度评分 ${Math.round(a.depth_score)}</p>
    </section>

    <div class="panel" style="margin-bottom:18px">
      <div class="toggle-row">
        <span class="muted">人设</span>
        <select id="persona" class="ghost-btn" style="border-radius:8px">
          ${Object.entries(PERSONAS).map(([k, v]) => `<option value="${k}">${v.name}</option>`).join("")}
        </select>
      </div>
      <div class="response-card ai" id="reply"></div>
      <p class="small muted" style="margin-top:10px">演示文案由 analysis-result 契约字段合成;真实生成接入 DeepSeek 模型(字段 <code>model</code>)。</p>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">本片段摘要与金句(契约字段)</h3>
      <p>${escapeHtml(a.summary)}</p>
      ${(a.golden_quotes || []).map((q) => `<div class="golden">“${escapeHtml(q.text)}”</div>`).join("")}
    </div>

    <div class="btn-row" style="margin-top:18px">
      <button class="btn secondary" id="toDetail">← 返回详情</button>
      <button class="btn" id="toExport">导出此片段 →</button>
    </div>`;

  const replyEl = root.querySelector("#reply");
  const personaSel = root.querySelector("#persona");
  const render = () => { replyEl.innerHTML = buildReply(a, personaSel.value).split("\n").map((l) => `<p>${l}</p>`).join(""); };
  personaSel.addEventListener("change", render);
  render();

  root.querySelector("#toDetail").addEventListener("click", () => location.hash = `#/detail/${a.segment_id}`);
  root.querySelector("#toExport").addEventListener("click", () => location.hash = `#/export/${a.segment_id}`);
}

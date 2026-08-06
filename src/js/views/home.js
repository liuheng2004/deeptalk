// 首页卡片流 —— 每张卡片对应一个 DeepTalkAnalysisResult 片段,
// 字段与 analysis-result.schema.json 一一对应。
import { getSession, getAnalyses, loadSample } from "../store.js";
import { computeMood, MOOD_LABEL } from "../data.js";
import { escapeHtml, formatDateTime, dimensionsHtml, animateDims } from "../util.js";

export function mount(root) {
  const session = getSession();
  const analyses = getAnalyses();

  if (!session || !analyses.length) {
    root.innerHTML = `
      <section class="page-head">
        <h1>深度对话卡片流</h1>
        <p>从导入的聊天记录中,自动识别值得纪念的深度对话。</p>
      </section>
      <div class="empty">
        <p>还没有数据。先导入一段聊天记录吧。</p>
        <div class="btn-row" style="justify-content:center">
          <button class="btn" id="go">去导入</button>
          <button class="btn secondary" id="demo">载入示例</button>
        </div>
      </div>`;
    root.querySelector("#go").addEventListener("click", () => location.hash = "#/import");
    root.querySelector("#demo").addEventListener("click", () => { loadSample(); render(); });
    return;
  }

  function render() {
    const cards = getAnalyses().map((a) => {
      const mood = computeMood(a);
      const quotes = (a.golden_quotes || []).slice(0, 2)
        .map((q) => escapeHtml(q.text)).join("　/　");
      return `
      <article class="talk-card mood-${mood}" data-seg="${escapeHtml(a.segment_id)}" tabindex="0" role="button" aria-label="查看片段 ${escapeHtml(a.segment_id)}">
        <div class="row">
          <div class="score" style="--val:${Math.round(a.depth_score)}"><b>${Math.round(a.depth_score)}</b><small>深度</small></div>
          <div>
            <h3>${escapeHtml(session.peer)}</h3>
            <div class="peer">${formatDateTime(a.start_time)} · ${Math.round(a.duration_minutes)} 分钟</div>
          </div>
          <span class="mood-chip" style="margin-left:auto">${MOOD_LABEL[mood]}态</span>
        </div>
        <p class="summary">${escapeHtml(a.summary)}</p>
        <div class="quotes">“${quotes}”</div>
        <div class="meta">
          <span>${(a.tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</span>
          ${a.is_deep ? `<span class="mood-chip">深度对话</span>` : `<span class="muted small">未达深度阈值</span>`}
        </div>
      </article>`;
    }).join("");

    root.innerHTML = `
      <section class="page-head">
        <h1>深度对话卡片流</h1>
        <p>会话:<b>${escapeHtml(session.peer)}</b> · 共 ${getAnalyses().length} 个片段 · 来源 ${escapeHtml(session.source || "—")}</p>
      </section>
      <div class="card-grid">${cards}</div>`;

    root.querySelectorAll(".talk-card").forEach((el) => {
      const seg = el.dataset.seg;
      const open = () => { location.hash = `#/detail/${seg}`; };
      el.addEventListener("click", open);
      el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
    });
  }

  render();
}

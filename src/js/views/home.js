// 首页卡片流 —— 每张卡片对应一个 DeepTalkAnalysisResult 片段,
// 字段与 analysis-result.schema.json 一一对应。
import { getSession, getAnalyses, loadSample } from "../store.js";
import { computeMood, MOOD_LABEL } from "../data.js";
import { escapeHtml, formatDateTime, dimensionsHtml, animateDims } from "../util.js";
import { orbitHTML, tickerHTML, initHero } from "../motion-hero.js";

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
      <section class="hero">
        <div class="hero-copy">
          <h1 class="hero-title">
            <span data-typewriter>把每一次深度对话，都变成<span class="grad">值得珍藏的卡片</span></span><span class="tw-cursor" aria-hidden="true"></span>
          </h1>
          <p class="hero-sub">导入微信导出或 AI 聊天截图，DeepSeek 在本地识别深度片段、金句与情绪，生成可回放、可导出的记忆卡片。纯本地运行，数据不出设备。</p>
          <div class="hero-actions">
            <a class="btn-border-wrap" href="#/import" aria-label="去导入">
              <span class="btn hero-cta">去导入
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
            </a>
            <button class="btn secondary" id="heroDemo">载入示例</button>
          </div>
        </div>
        ${orbitHTML(getAnalyses().length)}
      </section>
      ${tickerHTML()}
      <section class="page-head stream-head">
        <h1>深度对话卡片流</h1>
        <p>会话:<b>${escapeHtml(session.peer)}</b> · 共 ${getAnalyses().length} 个片段 · 来源 ${escapeHtml(session.source || "—")}</p>
      </section>
      <div class="card-grid">${cards}</div>`;

    initHero(root);
    const heroDemo = root.querySelector("#heroDemo");
    if (heroDemo) heroDemo.addEventListener("click", () => { loadSample(); render(); });

    root.querySelectorAll(".talk-card").forEach((el) => {
      const seg = el.dataset.seg;
      const open = () => { location.hash = `#/detail/${seg}`; };
      el.addEventListener("click", open);
      el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
    });
  }

  render();
}

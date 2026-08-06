// =====================================================================
// 影子回放(演进自 src/prototypes/shadow.html)
// 复用其「数据驱动节奏」内核:气泡浮现的疏密完全由消息时间戳间隔决定,
// 不写死任何动画时序。新增:
//   - 可作为模块挂载到任意容器(mountShadowReplay)
//   - 双态动效(joy/calm)局部配色与节奏
//   - 减弱动效开关(接收外部 reduced 状态)
//   - 全屏回放(Fullscreen API)
//   - 3–5s 循环滑块 + 重播
// =====================================================================

const PALETTE = {
  joy:  { me: "#9cc0ff", me2: "#3f6bd6", peer: "#ffc0a3", peer2: "#e8703f", breathe: 4200 },
  calm: { me: "#9cc0ff", me2: "#3f6bd6", peer: "#ffc0a3", peer2: "#e8703f", breathe: 7000 },
};

const FIG_SVG = (gradId, c1, c2) => `
<svg viewBox="0 0 200 320" aria-hidden="true">
  <defs><linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="${c1}"/><stop offset="1" stop-color="${c2}"/>
  </linearGradient></defs>
  <g fill="url(#${gradId})">
    <circle cx="100" cy="58" r="40"/>
    <path d="M40 320 C40 210 62 130 100 130 C138 130 160 210 160 320 Z"/>
    <path d="M100 150 C84 150 76 168 78 188 L74 250 L96 250 L96 170 Z"/>
    <path d="M100 150 C116 150 124 168 122 188 L126 250 L104 250 L104 170 Z"/>
  </g>
</svg>`;

export function mountShadowReplay(host, opts = {}) {
  const messages = opts.messages || [];
  const initialMood = opts.mood === "joy" ? "joy" : "calm";
  let loopMs = opts.loopMs || 4000;
  let reduced = opts.reduced || false;

  host.classList.add("replay-host");
  host.dataset.mood = initialMood;
  host.innerHTML = `
    <div class="stage" part="stage">
      <div class="floor"></div>
      <div class="figure me">${FIG_SVG("gMe", PALETTE[initialMood].me, PALETTE[initialMood].me2)}</div>
      <div class="figure peer">${FIG_SVG("gPeer", PALETTE[initialMood].peer, PALETTE[initialMood].peer2)}</div>
      <div class="bubble-layer me"></div>
      <div class="bubble-layer peer"></div>
      <div class="watermark">DeepTalk</div>
      <div class="progress"></div>
    </div>
    <div class="replay-toolbar">
      <button class="ghost-btn" data-act="replay" type="button">↻ 重播</button>
      <button class="ghost-btn" data-act="full" type="button">⛶ 全屏</button>
      <label>循环
        <input type="range" min="3000" max="5000" step="250" value="${loopMs}" data-act="loop" />
        <span class="loop-val">${(loopMs / 1000).toFixed(1)}s</span>
      </label>
      <label><input type="checkbox" data-act="reduce" ${reduced ? "checked" : ""}/> 减弱动效</label>
    </div>`;

  const stage = host.querySelector(".stage");
  const layerMe = host.querySelector(".bubble-layer.me");
  const layerPeer = host.querySelector(".bubble-layer.peer");
  const figMe = host.querySelector(".figure.me");
  const figPeer = host.querySelector(".figure.peer");
  const progress = host.querySelector(".progress");
  const loopInput = host.querySelector('[data-act="loop"]');
  const loopVal = host.querySelector(".loop-val");
  const reduceBox = host.querySelector('[data-act="reduce"]');

  let timers = [];
  let rafId = null;
  let cycleStart = 0;

  function applyMood(mood) {
    host.dataset.mood = mood;
    figMe.querySelector("linearGradient").setAttribute("id", "gMe");
    const g1 = figMe.querySelector("stop"); g1.setAttribute("stop-color", PALETTE[mood].me);
    const g2 = figMe.querySelectorAll("stop")[1]; g2.setAttribute("stop-color", PALETTE[mood].me2);
    const p1 = figPeer.querySelector("stop"); p1.setAttribute("stop-color", PALETTE[mood].peer);
    const p2 = figPeer.querySelectorAll("stop")[1]; p2.setAttribute("stop-color", PALETTE[mood].peer2);
  }

  function clearTimers() {
    timers.forEach(clearTimeout);
    timers = [];
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    layerMe.innerHTML = "";
    layerPeer.innerHTML = "";
    figMe.classList.remove("speaking");
    figPeer.classList.remove("speaking");
    host.classList.remove("reduced");
  }

  // 由消息时间戳计算间隔(ms),缺失则退化为顺序索引
  function toOffsets(msgs) {
    const ts = msgs.map((m) => Date.parse(m.timestamp));
    if (ts.some((t) => Number.isNaN(t))) {
      return msgs.map((_, i) => i * 1000);
    }
    const base = ts[0];
    return ts.map((t) => t - base);
  }

  function buildSchedule() {
    const offsets = toOffsets(messages);
    const totalReal = Math.max(offsets[offsets.length - 1], 1);
    const scale = loopMs / totalReal; // 等比缩放到循环窗口,间隔比例不变
    const schedule = [];
    let cum = 0;
    messages.forEach((m, i) => {
      const gap = i === 0 ? 0 : (offsets[i] - offsets[i - 1]) * scale;
      cum += gap;
      const live = Math.max(0.6, gap * 0.7);
      schedule.push({ ...m, appearAt: cum / 1000, live });
    });
    return schedule;
  }

  function spawnBubble(item) {
    const layer = item.sender === "me" ? layerMe : layerPeer;
    const fig = item.sender === "me" ? figMe : figPeer;
    const el = document.createElement("div");
    el.className = "bubble " + (item.sender === "me" ? "me" : "peer");
    el.textContent = item.content;
    const siblings = layer.querySelectorAll(".bubble:not(.gone)").length;
    el.style.bottom = siblings * 14 + "px";
    layer.appendChild(el);
    fig.classList.add("speaking");
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add("show")));
    const liveMs = item.live * 1000;
    const tHide = setTimeout(() => {
      el.classList.remove("show");
      el.classList.add("gone");
      fig.classList.remove("speaking");
      timers.push(setTimeout(() => el.remove(), 600));
    }, liveMs);
    timers.push(tHide);
  }

  function play() {
    clearTimers();
    if (reduced) host.classList.add("reduced");
    cycleStart = performance.now();
    const schedule = buildSchedule();
    schedule.forEach((item) => {
      timers.push(setTimeout(() => spawnBubble(item), item.appearAt * 1000));
    });
    const tick = (now) => {
      const p = Math.min(1, (now - cycleStart) / loopMs);
      progress.style.width = p * 100 + "%";
      if (p >= 1) { play(); return; }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
  }

  // ---- 交互 ----
  host.querySelector('[data-act="replay"]').addEventListener("click", play);
  loopInput.addEventListener("input", () => {
    loopMs = parseInt(loopInput.value, 10);
    loopVal.textContent = (loopMs / 1000).toFixed(1) + "s";
    play();
  });
  reduceBox.addEventListener("change", () => {
    reduced = reduceBox.checked;
    play();
  });
  host.querySelector('[data-act="full"]').addEventListener("click", () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else host.requestFullscreen?.();
  });
  host.addEventListener("fullscreenchange", () => {
    host.classList.toggle("fullscreen", document.fullscreenElement === host);
  });

  applyMood(initialMood);
  play();

  // 返回销毁句柄,便于路由切换时停止动画
  return {
    destroy() { clearTimers(); },
    setMood(m) { applyMood(m === "joy" ? "joy" : "calm"); },
    setReduced(v) { reduced = v; play(); },
  };
}

// =====================================================================
// Motion 皮肤动效:打字机标题 / 计数上抛 / 轨道头像装配 / 特性跑马灯。
// 设计参考:MotionSites 风格落地页。零外部依赖,尊重 html.reduced。
// =====================================================================
import { isReduced } from "./motion.js";

const EASE_OUT_CUBIC = (t) => 1 - Math.pow(1 - t, 3);

// 4 条同心轨道:尺寸 / 周期 / 转向(参考图 353→797px,30s→60s)
const RINGS = [
  {
    size: 353, dur: 30, dir: "reverse",
    avatars: [{ deg: 270, r: 177, face: "🌙", cls: "chip-1", delay: "0.6s" }],
  },
  {
    size: 501, dur: 40, dir: "normal",
    avatars: [
      { deg: 60, r: 251, face: "😌", cls: "chip-2", delay: "0.9s" },
      { deg: 180, r: 251, face: "💬", cls: "chip-3 big", delay: "1.1s" },
      { deg: 300, r: 251, face: "⭐", cls: "chip-4", delay: "1.3s" },
    ],
  },
  {
    size: 649, dur: 50, dir: "normal",
    avatars: [{ deg: 130, r: 325, face: "🧠", cls: "chip-5 big", delay: "1.6s" }],
  },
  {
    size: 797, dur: 60, dir: "reverse",
    avatars: [
      { deg: 30, r: 399, face: "🤖", cls: "chip-6", delay: "1.9s" },
      { deg: 95, r: 399, face: "💜", cls: "chip-7 bigx square", delay: "2.1s" },
      { deg: 220, r: 399, face: "✨", cls: "chip-8 bigx square", delay: "2.3s" },
      { deg: 320, r: 399, face: "☕", cls: "chip-9", delay: "1.4s" },
    ],
  },
];

export function orbitHTML(count) {
  const rings = RINGS.map((r) => {
    const dirRev = r.dir === "reverse" ? "normal" : "reverse";
    const avatars = r.avatars.map((a) => `
      <span class="orbit-avatar ${a.cls.includes("big") ? a.cls.match(/big\w*/)[0] : ""}" style="--deg:${a.deg}deg;--r:${a.r}px">
        <span class="avatar-spin" style="--dur:${r.dur}s;--dir-rev:${dirRev}">
          <span class="avatar-chip ${a.cls}" style="--delay:${a.delay}">${a.face}</span>
        </span>
      </span>`);
    return `
      <span class="orbit-ring" style="--size:${r.size}px;--dur:${r.dur}s;--dir:${r.dir}">
        ${avatars.join("")}
      </span>`;
  }).join("");

  return `
    <div class="orbit" role="img" aria-label="DeepTalk 记忆卡片轨道">
      ${rings}
      <div class="orbit-core">
        <b class="orbit-count" data-countup data-countup-target="${count}">0</b>
        <span>张记忆卡片</span>
      </div>
    </div>`;
}

export function tickerHTML() {
  const items = ["纯本地运行", "数据不出设备", "DeepSeek 驱动", "微信导出解析", "AI 聊天截图导入", "GPL-3.0 开源"];
  const chips = items.map((t) => `<span class="ticker-chip">${t}</span>`).join("");
  return `<div class="ticker"><div class="ticker-track">${chips}${chips}</div></div>`;
}

export function initHero(root) {
  initTypewriter(root);
  initCountUp(root);
}

function initTypewriter(root) {
  const el = root.querySelector("[data-typewriter]");
  if (!el) return;
  const text = el.textContent;
  if (isReduced()) return; // 已保留完整文本
  el.textContent = "";
  let i = 0;
  setTimeout(function step() {
    el.textContent = text.slice(0, ++i);
    if (i < text.length) setTimeout(step, 35);
  }, 400);
}

function initCountUp(root) {
  const el = root.querySelector("[data-countup]");
  if (!el) return;
  const target = Number(el.dataset.countupTarget || 0);
  if (isReduced()) { el.textContent = String(target); return; }
  const dur = 2000;
  const t0 = performance.now() + 1200;
  function frame(now) {
    const t = Math.min(1, Math.max(0, (now - t0) / dur));
    el.textContent = String(Math.round(EASE_OUT_CUBIC(t) * target));
    if (t < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

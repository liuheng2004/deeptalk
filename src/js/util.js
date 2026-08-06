// 小工具:HTML 转义、时间格式化、维度条渲染。
import { DIMENSIONS } from "./contracts.js";

export function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const WEEK = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

// ISO 时间 -> "2024-05-20 周一 22:01"
export function formatDateTime(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return escapeHtml(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${WEEK[d.getDay()]} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export function formatTime(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return escapeHtml(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}`;
}

// 距今描述(如「2 年前的今天」)
export function fromNow(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  const days = Math.round((now - d) / 86400000);
  if (days <= 0) return "今天";
  if (days < 30) return `${days} 天前`;
  if (days < 365) return `${Math.round(days / 30)} 个月前`;
  return `${Math.floor(days / 365)} 年前的今天`;
}

// 四维维度条 HTML(对应 analysis-result.dimensions)
export function dimensionsHtml(dimensions) {
  return `<div class="dims">` + DIMENSIONS.map(({ key, label }) => {
    const v = Math.round(dimensions?.[key] ?? 0);
    return `<div class="dim">
      <span>${label}</span>
      <span class="bar"><i data-w="${v}"></i></span>
      <span class="v">${v}</span>
    </div>`;
  }).join("") + `</div>`;
}

// 让维度条在挂载后做宽度动画
export function animateDims(root) {
  root.querySelectorAll(".dim .bar > i").forEach((el) => {
    requestAnimationFrame(() => { el.style.width = el.dataset.w + "%"; });
  });
}

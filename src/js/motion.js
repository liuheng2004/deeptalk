// =====================================================================
// 双态动效 + 减弱动效 控制。
// - 双态: html[data-mood="joy"|"calm"] 驱动全局配色与节奏(CSS 变量)。
// - 减弱动效: html.reduced 关闭过渡/动画;持久化到 localStorage,
//   并尊重系统 prefers-reduced-motion 偏好。
// =====================================================================

const KEY = "dt-reduced-motion";

export function initMotion() {
  const saved = localStorage.getItem(KEY);
  let reduced;
  if (saved === "1") reduced = true;
  else if (saved === "0") reduced = false;
  else reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  setReduced(reduced, false);

  const btn = document.getElementById("reduceToggle");
  if (btn) {
    btn.addEventListener("click", () => {
      setReduced(document.documentElement.classList.contains("reduced") ? false : true, true);
    });
  }
}

export function setReduced(on, persist = true) {
  document.documentElement.classList.toggle("reduced", on);
  if (on) document.documentElement.classList.remove("motion-allowed");
  else document.documentElement.classList.add("motion-allowed");
  const btn = document.getElementById("reduceToggle");
  if (btn) btn.setAttribute("aria-pressed", String(on));
  if (persist) localStorage.setItem(KEY, on ? "1" : "0");
}

export function isReduced() {
  return document.documentElement.classList.contains("reduced");
}

export function setMood(mood) {
  document.documentElement.setAttribute("data-mood", mood === "joy" ? "joy" : "calm");
}

export function getMood() {
  return document.documentElement.getAttribute("data-mood") || "calm";
}

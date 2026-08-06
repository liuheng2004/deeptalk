// =====================================================================
// 路由 + 启动。哈希路由: #/  #/import  #/detail/:seg  #/response/:seg  #/export/:seg
// =====================================================================
import { initMotion } from "./motion.js";
import { loadSample, isLoaded } from "./store.js";
import * as Home from "./views/home.js";
import * as Import from "./views/import.js";
import * as Detail from "./views/detail.js";
import * as Response from "./views/response.js";
import * as Export from "./views/export.js";

const view = document.getElementById("view");
let cleanup = null;

function parseHash() {
  const h = location.hash.replace(/^#/, "") || "/";
  const parts = h.split("/").filter(Boolean); // e.g. ["detail","seg-001"]
  if (parts.length === 0) return { name: "home", params: {} };
  const [head, seg] = parts;
  if (head === "import") return { name: "import", params: {} };
  if (head === "detail") return { name: "detail", params: { seg } };
  if (head === "response") return { name: "response", params: { seg } };
  if (head === "export") return { name: "export", params: { seg } };
  return { name: "home", params: {} };
}

function setActiveNav(route) {
  document.querySelectorAll(".mainnav a").forEach((a) => {
    const r = a.getAttribute("data-route");
    a.classList.toggle("active", (r === "/" && route.name === "home") || (r === "/import" && route.name === "import"));
  });
}

function render() {
  const route = parseHash();
  if (typeof cleanup === "function") { try { cleanup(); } catch (_) {} cleanup = null; }

  view.scrollTop = 0;
  view.focus({ preventScroll: true });

  switch (route.name) {
    case "import": Import.mount(view); break;
    case "detail": cleanup = Detail.mount(view, route.params); break;
    case "response": Response.mount(view, route.params); break;
    case "export": Export.mount(view, route.params); break;
    default: Home.mount(view);
  }
  setActiveNav(route);
}

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", () => {
  initMotion();
  if (!isLoaded()) loadSample(); // 首次进入即载入示例,便于直接演示卡片流
  render();
});

// 若脚本在 DOMContentLoaded 之后才执行(模块通常延迟),手动触发一次
if (document.readyState !== "loading") {
  initMotion();
  if (!isLoaded()) loadSample();
  render();
}

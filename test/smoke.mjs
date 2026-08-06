// DOM 冒烟测试:用 jsdom 真实挂载每个视图,捕获运行时错误。
import { JSDOM } from "jsdom";
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const html = readFileSync(join(root, "src/index.html"), "utf8");

const dom = new JSDOM(html, { url: "http://localhost/", pretendToBeVisual: true });
const { window } = dom;

// ---- 浏览器 API 垫片 ----
window.matchMedia = window.matchMedia || (() => ({ matches: false, addEventListener() {}, removeEventListener() {} }));
window.requestAnimationFrame = window.requestAnimationFrame || ((cb) => setTimeout(() => cb(performance.now()), 0));
window.cancelAnimationFrame = window.cancelAnimationFrame || ((id) => clearTimeout(id));
window.HTMLCanvasElement.prototype.getContext = function () {
  const noop = () => {};
  return new Proxy({}, {
    get(_, p) {
      if (p === "measureText") return () => ({ width: 10 });
      if (p === "createLinearGradient") return () => ({ addColorStop: noop });
      return noop;
    },
    set() { return true; },
  });
};
window.Element.prototype.requestFullscreen = function () { return Promise.resolve(); };
Object.defineProperty(window.document, "fullscreenElement", { get: () => null, configurable: true });

// 暴露给模块(它们在 Node 全局查找这些)
for (const k of ["document","location","localStorage","requestAnimationFrame","cancelAnimationFrame","matchMedia","FileReader","HTMLCanvasElement","Element","Node","getComputedStyle"]) {
  try { globalThis[k] = window[k] ?? globalThis[k]; } catch { /* 只读全局跳过 */ }
}
globalThis.window = window;
globalThis.document = window.document;
globalThis.location = window.location;
globalThis.localStorage = window.localStorage;

const errors = [];
window.addEventListener("error", (e) => errors.push("window.error: " + (e.error?.stack || e.message)));
const origErr = console.error;
console.error = (...a) => { errors.push("console.error: " + a.join(" ")); origErr(...a); };

async function run() {
  const view = window.document.getElementById("view");
  const wait = (ms = 20) => new Promise((res) => setTimeout(res, ms));
  async function go(hash, expect) {
    window.location.hash = hash;
    window.dispatchEvent(new window.Event("hashchange"));
    await wait();
    if (!window.document.querySelector(expect)) errors.push(`路由 ${hash} 未渲染预期节点 ${expect}`);
  }

  // 导入 main.js(其内部会在 DOMContentLoaded/readyState 时渲染)
  await import(pathToFileURL(join(root, "src/js/main.js")).href);
  await wait();

  await go("#/", ".talk-card");
  const cardCount = view.querySelectorAll(".talk-card").length;
  await go("#/import", "#parse");
  await go("#/detail/seg-001", ".replay-host");
  await go("#/response/seg-001", "#reply");
  await go("#/export/seg-001", "#cv");
  await go("#/detail/seg-002", ".replay-host");
  await go("#/export/seg-003", "#cv");

  if (errors.length) {
    console.log("❌ 渲染校验失败:\n" + errors.join("\n"));
    process.exit(1);
  }
  console.log(`✅ 全部 7 条路由挂载无运行时错误;首页卡片流渲染 ${cardCount} 张卡片`);
  process.exit(0);
}
run();

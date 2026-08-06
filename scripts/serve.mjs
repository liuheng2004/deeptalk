// 零依赖静态文件服务器 —— 用于离线演示 DeepTalk 前端 UI。
// 用法: node scripts/serve.mjs [port]
// 访问: http://localhost:<port>/  (自动指向 src/index.html)
import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import { join, normalize, extname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = normalize(join(fileURLToPath(import.meta.url), "..", ".."));
const PORT = Number(process.argv[2] || process.env.PORT || 5173);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".md": "text/markdown; charset=utf-8",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

const server = http.createServer(async (req, res) => {
  try {
    let urlPath = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    if (urlPath === "/") urlPath = "/src/index.html";

    // 防目录穿越
    const safe = normalize(join(ROOT, urlPath));
    if (!safe.startsWith(ROOT)) {
      res.writeHead(403).end("Forbidden");
      return;
    }

    let filePath = safe;
    try {
      const s = await stat(filePath);
      if (s.isDirectory()) filePath = join(filePath, "index.html");
    } catch {
      // 单页应用:未知非资源路径回退到 src/index.html
      if (!extname(urlPath)) filePath = join(ROOT, "src/index.html");
    }

    const data = await readFile(filePath);
    const type = MIME[extname(filePath)] || "application/octet-stream";
    res.writeHead(200, { "Content-Type": type, "Cache-Control": "no-cache" });
    res.end(data);
  } catch (err) {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("404 Not Found\n" + (err?.message || ""));
  }
});

server.listen(PORT, () => {
  console.log(`DeepTalk 前端演示已启动: http://localhost:${PORT}/`);
  console.log(`(项目根: ${ROOT})`);
});

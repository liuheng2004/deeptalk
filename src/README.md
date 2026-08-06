# src

前端 UI:导入向导、卡片流、双态动效、完整剪影版影子回放、导出面板。

负责人:CodeBuddy(hy3)。此目录由 CodeBuddy 维护。

## 结构

```
src/
├── index.html              # SPA 入口(哈希路由)
├── styles/app.css          # 全局样式 + 双态(愉悦/平静)令牌 + 减弱动效
├── CONTRACT_MAPPING.md     # 界面字段 ↔ docs/contracts 一一对应说明
├── prototypes/shadow.html  # 剪影动画原型(影子回放演进来源)
└── js/
    ├── main.js             # 哈希路由 + 启动
    ├── contracts.js        # 契约字段定义(唯一事实来源)
    ├── data.js             # 示例 ChatSession / AnalysisResult(严格符合契约)
    ├── store.js            # 内存数据
    ├── motion.js           # 双态 + 减弱动效控制
    ├── shadow.js           # 可复用影子回放(数据驱动节奏)
    ├── util.js             # 转义 / 时间格式化 / 维度条
    └── views/
        ├── import.js       # 导入页
        ├── home.js         # 首页卡片流
        ├── detail.js       # 对话详情页(内嵌影子回放)
        ├── response.js     # 回应页
        └── export.js       # 导出面板(PNG/PDF/MD)
```

## 本地运行(零依赖)

```bash
npm run dev          # 启动 scripts/serve.mjs,访问 http://localhost:5173/
```

> 也可 `npm run dev:vite` 走 Vite 构建链路(需先 `npm install` 安装 Tauri/Vite 依赖)。
> 冒烟测试:`npm test`(jsdom 挂载全部路由,校验无运行时错误)。

## 字段对应

所有展示字段均来自 `docs/contracts/`,详见 `src/CONTRACT_MAPPING.md`。

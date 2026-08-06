# DeepTalk

DeepTalk 是一款「微信深度对话的记忆与回应工具」:从微信导出的聊天记录中自动识别值得纪念的深度对话,生成可翻阅、可预览的记忆卡片(带对话影子动画),并由内置 AI Agent 给出有温度的第三方回应,支持导出为图片 / PDF / Markdown。

## 功能特性

- **导入**:微信官方「邮件发送聊天记录」导出的 txt(纯文本,图片不导入);
- **识别**:AI 自动分段、四维打分(情感 / 事件 / 连续性 / 互动)、摘要与金句;
- **卡片**:堆叠式卡片流 + 愉悦 / 平静双态动效 + 完整剪影版影子回放;
- **回应**:DeepSeek-V4-Flash 驱动的第三方视角回应,多种人设可选;
- **导出**:图片(PNG)/ PDF / Markdown 三种格式,品牌水印可关闭;
- **隐私**:纯本地运行,数据不出设备,本地加密存储。

## 快速开始

> 构建命令待 M1 初始化后补充完整,以下为基本流程。

```bash
# 1. 克隆仓库(GitHub 远端尚未创建;创建并推送后,替换为实际地址)
git clone <remote-url> deeptalk
cd deeptalk

# 2. 配置环境变量(填入 DeepSeek API Key)
cp .env.example .env

# 3. 安装前端依赖并启动 Tauri 开发模式
npm install
npm run tauri dev
```

环境要求:Node.js LTS、Rust(rustup)、Tauri 2 依赖(Windows 需 WebView2)。

## 项目文档

| 文档 | 位置 |
|------|------|
| 接口契约(会话模型 / 识别结果 / 导出模板) | [docs/contracts/](docs/contracts/) |
| 多智能体协作搭建清单 | 见项目工作区 `projects/project-003/docs/多智能体协作搭建清单.md` |

## 目录结构

```
deeptalk/
├── src-tauri/       # Tauri / Rust 桌面端(本地存储、系统集成)
├── src/             # 前端 UI(卡片、动效、导出)
├── core/
│   ├── parser/      # 微信 txt 解析与清洗
│   └── analysis/    # 识别引擎 + 模型接入抽象层
├── tests/           # 单测与集成测试
├── scripts/         # 构建 / 打包 / 发布脚本
└── docs/            # 契约与文档
```

## 开源协议

[MIT](LICENSE)

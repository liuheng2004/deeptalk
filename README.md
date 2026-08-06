# DeepTalk

DeepTalk 是一款「微信深度对话的记忆与回应工具」:从微信导出的聊天记录中自动识别值得纪念的深度对话,生成可翻阅、可预览的记忆卡片(带对话影子动画),并由内置 AI Agent 给出有温度的第三方回应,支持导出为图片 / PDF / Markdown。

## 功能特性

- **导入**:微信官方「邮件发送聊天记录」导出的 txt(纯文本,图片不导入);
- **识别**:AI 自动分段、四维打分(情感 / 事件 / 连续性 / 互动)、摘要与金句;
- **卡片**:堆叠式卡片流 + 愉悦 / 平静双态动效 + 完整剪影版影子回放;
- **回应**:DeepSeek-V4-Flash 驱动的第三方视角回应,多种人设可选;
- **导出**:图片(PNG)/ PDF / Markdown 三种格式,品牌水印可关闭;
- **隐私**:纯本地运行,数据不出设备,本地加密存储。

## 安装(Windows 内测包)

v0.1 内测包通过 GitHub Releases 发布:访问 [liuheng2004/deeptalk Releases](https://github.com/liuheng2004/deeptalk/releases),下载 `DeepTalk_0.1.0_x64-setup.exe`,双击按提示安装即可。

- **系统要求**:Windows 10/11(x64),需 WebView2 运行时(Windows 10/11 一般已内置;缺失时安装程序会引导下载)。
- **SmartScreen 说明**:安装包目前未做代码签名,首次运行时 Windows SmartScreen 可能提示「Windows 已保护你的电脑」。这是正常现象,点击 **更多信息 → 仍要运行** 即可继续;也可以在文件资源管理器中右键安装包 → 属性 → 勾选 **解除锁定** → 确定后再次双击。企业环境如需批量安装,请联系管理员放行或加入例外策略。
- **数据位置**:应用数据(含本地加密的主密钥)保存在当前用户的 `%APPDATA%\deeptalk`;卸载应用不会自动删除该目录,请自行备份。

## 从源码构建

```bash
# 1. 克隆仓库
git clone https://github.com/liuheng2004/deeptalk.git
cd deeptalk

# 2. 配置环境变量(填入 DeepSeek API Key)
cp .env.example .env

# 3. 安装前端依赖
npm install

# 4. 开发模式运行
npm run tauri dev

# 5. 打包 Windows 安装包(NSIS exe)
npm run tauri build
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

[GPL-3.0](LICENSE)

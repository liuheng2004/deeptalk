# DeepTalk 集成联调 E2E

M1-6:导入 → 识别 → 卡片 → 回应 → 导出 全链路已打通。

## 运行环境

- Python 3.5+ (纯标准库,零第三方依赖)
- Node.js 12+ (导出渲染:pureimage + pdfkit,见 `scripts/render/`)
- Windows 系统字体(SimHei / 微软雅黑)用于中文渲染

## 快速开始

```bash
# 安装导出渲染依赖(仅需一次)
cd scripts/render && npm install && cd ../..

# 全链路运行(默认:有 DeepSeek Key 走 API,无 Key 走本地规则,均可用)
python core/cli.py run docs/guides/wechat-export-samples/sample-01-basic-daily.txt --outdir out

# 强制本地规则(离线演示)
python core/cli.py run docs/guides/wechat-export-samples/sample-02-rich-features.txt --outdir out --local

# 强制 API
python core/cli.py run docs/guides/wechat-export-samples/sample-02-rich-features.txt --outdir out --api

# 单步:解析 / 识别
python core/cli.py parse docs/guides/wechat-export-samples/sample-01-basic-daily.txt
python core/cli.py analyze docs/guides/wechat-export-samples/sample-01-basic-daily.txt
```

## 测试

```bash
python scripts/run_tests.py
```

覆盖:三份样例解析(时间推断、撤回、语音转文字、引用、拍一拍、多行、跨天)、
识别结果结构、卡片构建、全链路 E2E(导出 PNG/PDF/Markdown 校验)。

## 目录结构

```
core/parser/      微信 txt 解析 -> ChatSession(session.schema.json)
core/analysis/    分段、四维打分、深度评分、摘要、金句(analysis-result.schema.json)
core/card/        卡片数据模型
core/response/    第三方回应(DeepSeek / 本地模板)
core/export/      Markdown(纯 Python)+ PNG/PDF(Node 渲染器)
core/pipeline.py  全链路编排
scripts/run_tests.py    测试入口
scripts/render/   导出渲染器(Node:pureimage + pdfkit)
```

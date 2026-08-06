# 文档

## 契约

| 文档 | 说明 | 负责人 |
|------|------|--------|
| [contracts/session.schema.json](contracts/session.schema.json) | 会话数据模型(解析器输出) | Claude 起草 / SMOKE-CLAUDE 定稿 |
| [contracts/analysis-result.schema.json](contracts/analysis-result.schema.json) | 识别引擎输出 | Claude 起草 / SMOKE-CLAUDE 定稿 |
| [contracts/export-template.md](contracts/export-template.md) | PNG / PDF / MD 导出排版规范 | Claude 起草 / SMOKE-CLAUDE 定稿 |

> 规则:任何字段变更必须走 PR 更新对应 Schema,并由 Codex 在 CI 中加校验。

## 解析规格与样例

| 文档 | 说明 | 负责人 |
|------|------|--------|
| [guides/parser-spec.md](guides/parser-spec.md) | 微信 txt 解析规格(时间行 / 消息类型 / 时间戳推断策略) | ArkAgent 起草 |
| [guides/wechat-export-samples/](guides/wechat-export-samples/) | 微信导出脱敏样例(3 份) | ArkAgent 起草 |
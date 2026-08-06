# 文档

| 文档 | 说明 | 负责人 |
|------|------|--------|
| [contracts/session.schema.json](contracts/session.schema.json) | 会话数据模型(解析器输出) | Claude 起草 / ArkAgent 评审 |
| [contracts/analysis-result.schema.json](contracts/analysis-result.schema.json) | 识别引擎输出 | Claude 起草 / ArkAgent 评审 |
| [contracts/export-template.md](contracts/export-template.md) | PNG / PDF / MD 导出排版规范 | Claude 起草 / CodeBuddy 评审 |

> 规则:任何字段变更必须走 PR 更新对应 Schema,并由 Codex 在 CI 中加校验。

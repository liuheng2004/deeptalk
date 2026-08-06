# 前端字段 ↔ 契约 一一对应说明

本目录实现的前端 UI,其展示字段严格来自 `docs/contracts/` 三份契约。
下方逐页列出「界面元素 → 契约字段」的映射,作为 M1-4 验收依据。

## 1. 导入页 `views/import.js`
| 界面 | 契约 | 字段 |
|------|------|------|
| 解析后产出 | session.schema.json | `session_id` `peer` `created_at` `updated_at` `source` `message_count` `messages[]` `note` |
| 消息子结构 | session.schema.json#/definitions/message | `id` `sender` `content` `type` `timestamp` `inferred_time` `quote_of` |

> 真实解析由 `core/parser` 负责;本页仅做 UI 演示,加载符合上述结构的示例会话。

## 2. 首页卡片流 `views/home.js`
每张卡片对应一个 `DeepTalkAnalysisResult`:
| 卡片元素 | 契约字段 |
|----------|----------|
| 对方昵称 | session.peer(经 session_id 关联) |
| 深度评分数字 | analysis-result.depth_score |
| 片段时间 / 时长 | analysis-result.start_time / duration_minutes |
| 双态徽标(愉悦/平静) | 由 dimensions 推导(见下),非新增存储字段 |
| 摘要 | analysis-result.summary |
| 金句(前 2 条) | analysis-result.golden_quotes[].text |
| 主题标签 | analysis-result.tags[] |
| 是否深度对话 | analysis-result.is_deep |

## 3. 对话详情页 `views/detail.js`
| 元素 | 契约字段 |
|------|----------|
| 深度评分环 | analysis-result.depth_score |
| 阈值 / 模型 | analysis-result.threshold / model |
| 起止时间 / 距今 | analysis-result.start_time / end_time |
| 四维维度条 | analysis-result.dimensions.{emotion,event,continuity,interaction} |
| 摘要 | analysis-result.summary |
| 金句 | analysis-result.golden_quotes[].text |
| 完整对话 | analysis-result.messages[](结构与 message 一致) |
| 发送者 / 时间 / 类型 / 推断 | message.sender / timestamp / type / inferred_time |

**影子回放**(演进自 `prototypes/shadow.html`):气泡浮现节奏完全由
`analysis-result.messages[].timestamp` 的相邻间隔驱动,不写死时序。

## 4. 回应页 `views/response.js`
| 元素 | 契约字段 |
|------|----------|
| 摘要引用 | analysis-result.summary |
| 金句引用 | analysis-result.golden_quotes[].text |
| 维度引用 | analysis-result.dimensions.{emotion,interaction} |
| AI 文案(演示) | 由上述字段合成;真实生成写入 analysis-result.model 指定模型 |

## 5. 导出面板 `views/export.js`(遵循 export-template.md)
| 元素 | 契约字段 / 规范 |
|------|------|
| PNG 1080×1440 | 日期 + 距今(start_time/fromNow)、标签、金句、昵称、评分、水印 |
| Markdown front matter | title/tags/session_id + peer/depth_score(from 契约) |
| PDF | 摘要 + 金句 + 完整对话(契约字段) |
| 水印开关 | export-template.md「水印」规则(默认开) |
| 隐私开关 | export-template.md「分享隐私」(默认隐藏昵称/评分) |

## 双态推导规则(演示用,纯计算)
```
joy  = dimensions.emotion + dimensions.event
calm = dimensions.continuity + dimensions.interaction
mood = joy > calm ? "joy" : "calm"   // 同分取平静
```
仅使用契约既有字段,不向契约新增任何存储字段。

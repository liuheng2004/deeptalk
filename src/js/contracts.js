// =====================================================================
// 契约字段定义 —— 前端展示的唯一事实来源。
// 这里的每一项都对应 docs/contracts/ 中的 schema 字段,
// 视图层只从本模块读取字段名 / 标签,保证「与契约一一对应」。
// =====================================================================

// session.schema.json (ChatSession)
export const SESSION_FIELDS = [
  { key: "session_id", label: "会话 ID", required: true },
  { key: "peer", label: "对方昵称", required: true },
  { key: "created_at", label: "创建时间", required: true, type: "date-time" },
  { key: "updated_at", label: "更新时间", required: false, type: "date-time" },
  { key: "source", label: "导入来源", required: false },
  { key: "message_count", label: "消息条数", required: false, type: "integer" },
  { key: "note", label: "解析说明", required: false },
  // messages[] 中的 message 子字段
  { key: "messages", label: "消息列表", required: true, isArray: true },
];

// session.message 子结构
export const MESSAGE_FIELDS = [
  { key: "id", label: "消息 ID", required: true },
  { key: "sender", label: "发送者", required: true },
  { key: "content", label: "内容", required: true },
  { key: "type", label: "类型", required: false, enum: ["text", "voip_text", "quote", "system"] },
  { key: "timestamp", label: "时间", required: true, type: "date-time" },
  { key: "inferred_time", label: "推断时间", required: false, type: "boolean" },
  { key: "quote_of", label: "引用自", required: false },
];

// analysis-result.schema.json (DeepTalkAnalysisResult)
export const ANALYSIS_FIELDS = [
  { key: "segment_id", label: "片段 ID", required: true },
  { key: "session_id", label: "所属会话", required: true },
  { key: "depth_score", label: "深度评分", required: true, type: "number(0-100)" },
  { key: "threshold", label: "深度阈值", required: false, type: "number(0-100)" },
  { key: "is_deep", label: "是否深度对话", required: false, type: "boolean" },
  { key: "start_time", label: "开始时间", required: true, type: "date-time" },
  { key: "end_time", label: "结束时间", required: true, type: "date-time" },
  { key: "duration_minutes", label: "持续分钟", required: false, type: "number" },
  { key: "summary", label: "摘要", required: true },
  { key: "tags", label: "主题标签", required: false, isArray: true },
  { key: "golden_quotes", label: "金句", required: false, isArray: true },
  { key: "model", label: "生成模型", required: false },
  // messages[] 复用 session.message 结构
  { key: "messages", label: "片段消息", required: true, isArray: true },
];

// 四维维度(analysis-result.dimensions)
export const DIMENSIONS = [
  { key: "emotion", label: "情感深度" },
  { key: "event", label: "关键节点" },
  { key: "continuity", label: "主题连续" },
  { key: "interaction", label: "互动质量" },
];

export const MESSAGE_TYPE_LABEL = {
  text: "文本",
  voip_text: "语音转文字",
  quote: "引用",
  system: "系统",
};

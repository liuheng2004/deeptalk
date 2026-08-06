// =====================================================================
// 示例数据 —— 严格遵循 docs/contracts/ 的 schema。
// 仅用于前端演示;真实数据由 core/parser + core/analysis 产出。
// =====================================================================

// ---- ChatSession (session.schema.json) ----
export const SAMPLE_SESSION = {
  session_id: "sess-2024-0520-linx",
  peer: "林夕",
  created_at: "2024-05-20T22:01:10+08:00",
  updated_at: "2024-05-20T23:48:02+08:00",
  source: "wechat-email-txt",
  message_count: 11,
  note: "部分时间戳由相邻消息间隔推断(标记 inferred_time)。",
  messages: [
    { id: "m1",  sender: "me",   content: "你最近睡得还好吗?",          type: "text", timestamp: "2024-05-20T22:01:10+08:00" },
    { id: "m2",  sender: "林夕", content: "不太好,总在想以后的事。",     type: "text", timestamp: "2024-05-20T22:01:45+08:00" },
    { id: "m3",  sender: "me",   content: "说给我听听。",                type: "text", timestamp: "2024-05-20T22:02:05+08:00" },
    { id: "m4",  sender: "林夕", content: "怕选错路,又怕原地踏步。",     type: "text", timestamp: "2024-05-20T22:03:00+08:00" },
    { id: "m5",  sender: "me",   content: "其实你已经在走了。",          type: "text", timestamp: "2024-05-20T22:03:10+08:00" },
    { id: "m6",  sender: "林夕", content: "被你这句话接住了。",          type: "text", timestamp: "2024-05-20T22:04:30+08:00" },
    { id: "m7",  sender: "me",   content: "想换城市的事,要不要列个清单?", type: "text", timestamp: "2024-05-20T22:20:00+08:00" },
    { id: "m8",  sender: "林夕", content: "好,明早一起捋。",            type: "text", timestamp: "2024-05-20T22:21:12+08:00" },
    { id: "m9",  sender: "me",   content: "「一起」这两个字挺暖的。",    type: "quote", timestamp: "2024-05-20T22:22:00+08:00", quote_of: "m8" },
    { id: "m10", sender: "林夕", content: "明天见,晚安。",              type: "text", timestamp: "2024-05-20T23:40:00+08:00", inferred_time: true },
    { id: "m11", sender: "me",   content: "晚安,别想太多。",            type: "text", timestamp: "2024-05-20T23:48:02+08:00", inferred_time: true },
  ],
};

// ---- DeepTalkAnalysisResult[] (analysis-result.schema.json) ----
export const SAMPLE_ANALYSES = [
  {
    segment_id: "seg-001",
    session_id: "sess-2024-0520-linx",
    depth_score: 87,
    threshold: 60,
    is_deep: true,
    dimensions: { emotion: 92, event: 78, continuity: 64, interaction: 81 },
    start_time: "2024-05-20T22:01:10+08:00",
    end_time: "2024-05-20T22:04:30+08:00",
    duration_minutes: 3.3,
    summary: "关于未来与职业选择的深夜长谈。林夕坦露对「选错路」的焦虑,我在倾听中给予了确认与接住,情绪在结尾被温柔托住。",
    tags: ["深夜emo", "职业选择", "被接住"],
    golden_quotes: [
      { text: "怕选错路,又怕原地踏步。", message_id: "m4" },
      { text: "其实你已经在走了。", message_id: "m5" },
      { text: "被你这句话接住了。", message_id: "m6" },
    ],
    model: "deepseek-v4-flash",
    messages: ["m1","m2","m3","m4","m5","m6"].map(pick),
  },
  {
    segment_id: "seg-002",
    session_id: "sess-2024-0520-linx",
    depth_score: 71,
    threshold: 60,
    is_deep: true,
    dimensions: { emotion: 58, event: 40, continuity: 86, interaction: 90 },
    start_time: "2024-05-20T22:20:00+08:00",
    end_time: "2024-05-20T22:22:00+08:00",
    duration_minutes: 2.0,
    summary: "从焦虑转向具体的行动计划。我提议列清单,林夕欣然应允,并以「一起」收束,互动质量与连续性很高,节奏舒缓。",
    tags: ["行动计划", "一起", "平静"],
    golden_quotes: [
      { text: "好,明早一起捋。", message_id: "m8" },
      { text: "「一起」这两个字挺暖的。", message_id: "m9" },
    ],
    model: "deepseek-v4-flash",
    messages: ["m7","m8","m9"].map(pick),
  },
  {
    segment_id: "seg-003",
    session_id: "sess-2024-0520-linx",
    depth_score: 38,
    threshold: 60,
    is_deep: false,
    dimensions: { emotion: 30, event: 12, continuity: 44, interaction: 52 },
    start_time: "2024-05-20T23:40:00+08:00",
    end_time: "2024-05-20T23:48:02+08:00",
    duration_minutes: 8.0,
    summary: "收尾的晚安道别。林夕因时间戳缺失被推断为 23:40,互动平稳但未达深度阈值。",
    tags: ["晚安", "收尾"],
    golden_quotes: [
      { text: "明天见,晚安。", message_id: "m10" },
    ],
    model: "deepseek-v4-flash",
    messages: ["m10","m11"].map(pick),
  },
];

function pick(id) {
  const m = SAMPLE_SESSION.messages.find((x) => x.id === id);
  // 复制一份,避免视图误改示例源数据
  return { ...m };
}

// =====================================================================
// 双态推导(演示):仅由契约字段计算得到,不新增存储字段。
//   愉悦(joy)  = 情感(emotion) + 关键节点(event) 较高 → 暖、活跃
//   平静(calm) = 主题连续(continuity) + 互动(interaction) 较高 → 冷、舒缓
// 同分时取 平静,体现「默认更温和」的基调。
// =====================================================================
export function computeMood(result) {
  const d = result.dimensions;
  const joy = (d.emotion || 0) + (d.event || 0);
  const calm = (d.continuity || 0) + (d.interaction || 0);
  return joy > calm ? "joy" : "calm";
}

export const MOOD_LABEL = { joy: "愉悦", calm: "平静" };

/**
 * 导出模块的数据模型与选项。
 *
 * 字段尽量对齐 `docs/contracts/session.schema.json` 与
 * `docs/contracts/analysis-result.schema.json`,便于直接接入解析器与分析引擎的输出。
 */

/** 单条消息(结构同 session.schema.json 的 message 定义)。 */
export interface ChatMessage {
  id: string;
  /** 发送者昵称;本机统一记为 "me"。 */
  sender: string;
  content: string;
  type?: 'text' | 'voip_text' | 'quote' | 'system';
  /** ISO 时间字符串。 */
  timestamp: string;
  /** 时间戳是否为推断值。 */
  inferred_time?: boolean;
  /** 被引用的消息 id(可选)。 */
  quote_of?: string;
}

/** 规范化会话(对齐 session.schema.json)。 */
export interface ChatSession {
  session_id: string;
  peer: string;
  created_at: string;
  updated_at?: string;
  source?: string;
  message_count?: number;
  messages: ChatMessage[];
  note?: string;
}

/** 金句(对齐 analysis-result.schema.json)。 */
export interface GoldenQuote {
  text: string;
  message_id: string;
}

/** 四维评分。 */
export interface DimensionScores {
  emotion: number;
  event: number;
  continuity: number;
  interaction: number;
}

/** 深度对话识别结果(对齐 analysis-result.schema.json)。 */
export interface AnalysisResult {
  segment_id: string;
  session_id: string;
  depth_score: number;
  threshold?: number;
  is_deep?: boolean;
  dimensions: DimensionScores;
  start_time: string;
  end_time: string;
  duration_minutes?: number;
  summary: string;
  tags: string[];
  golden_quotes: GoldenQuote[];
  messages: ChatMessage[];
  model?: string;
}

/**
 * 一次导出所需的全部输入。
 *
 * `aiResponse` 为 AI 第三方回应文本,当前 analysis-result schema 尚未收录该字段,
 * 故在导出层作为可选输入承接(见 docs/contracts/export-template.md 的 PDF/MD 结构)。
 */
export interface ExportInput {
  session: ChatSession;
  analysis: AnalysisResult;
  aiResponse?: string;
}

/** 导出格式。 */
export type ExportFormat = 'png' | 'pdf' | 'md';

/** 导出选项。 */
export interface ExportOptions {
  format: ExportFormat;
  /**
   * 是否带品牌水印。
   * - PNG:默认右下角半透明「DeepTalk」水印,可关闭(见 export-template.md)。
   * - PDF:封面 logo 与页脚小字为结构性品牌信息,始终保留。
   * 可通过环境变量 `DEEPTALK_WATERMARK=false` 改变默认值。
   */
  watermark?: boolean;
  /**
   * 是否显示敏感字段(对方昵称 / 深度评分)。
   * 默认 false:隐藏昵称(显示「匿名」)、隐藏评分,符合隐私默认策略。
   */
  showSensitive?: boolean;
  /** 中文字体路径(ttf/otf)。默认自动探测系统字体。 */
  cjkFontPath?: string;
  /** 品牌名称,默认 "DeepTalk"。 */
  brand?: string;
}

/** 时间标注(所有格式均须包含)。 */
export interface TimeInfo {
  /** 2024年5月20日 星期一 */
  dateLabel: string;
  /** 22:13 */
  startTimeLabel: string;
  /** 23:47 */
  endTimeLabel: string;
  /** 22:13 - 23:47 */
  rangeLabel: string;
  /** 1小时34分钟 */
  durationLabel: string;
  /** 2年前的今天 / 约2年前 */
  sinceLabel: string;
}

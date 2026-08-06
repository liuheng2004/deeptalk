import type { ExportInput, ExportOptions } from './types.js';
import { peerLabel } from './privacy.js';

/** 由昵称 + 首个标签生成导出标题(用于 PDF 封面与 MD 标题)。 */
export function buildTitle(input: ExportInput, opts: ExportOptions): string {
  const peer = peerLabel(input, opts);
  const tag = input.analysis.tags[0];
  if (tag) return `${peer}的长谈:${tag}`;
  return `${peer}的深度对话`;
}

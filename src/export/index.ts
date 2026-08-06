import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import type { ExportInput, ExportOptions } from './types.js';
import { renderPng } from './png.js';
import { renderPdf } from './pdf.js';
import { renderMarkdown } from './markdown.js';

export * from './types.js';
export { buildTimeInfo, formatSince, formatDuration, formatDateLabel, formatClock } from './time.js';
export { resolveCjkFont } from './fonts.js';
export { peerLabel, scoreVisible } from './privacy.js';
export { buildTitle } from './title.js';
export { renderPng, renderPdf, renderMarkdown };

/** 解析水印默认值:环境变量 DEEPTALK_WATERMARK 可整体关闭水印。 */
function resolveWatermark(opts: ExportOptions): boolean {
  if (typeof opts.watermark === 'boolean') return opts.watermark;
  if (process.env.DEEPTALK_WATERMARK === 'false') return false;
  return true;
}

/** 规整导出选项,补齐默认值。 */
export function normalizeOptions(
  opts: ExportOptions,
): Required<Pick<ExportOptions, 'watermark' | 'showSensitive'>> & ExportOptions {
  return {
    ...opts,
    watermark: resolveWatermark(opts),
    showSensitive: opts.showSensitive === true,
  };
}

/** 渲染为内存 Buffer(PNG/PDF 为二进制,MD 为 UTF-8 文本)。 */
export async function exportToBuffer(
  input: ExportInput,
  opts: ExportOptions,
): Promise<Buffer | string> {
  const eff = normalizeOptions(opts);
  switch (eff.format) {
    case 'png':
      return renderPng(input, eff);
    case 'pdf':
      return renderPdf(input, eff);
    case 'md':
      return renderMarkdown(input, eff);
    default:
      throw new Error(`不支持的导出格式:${(eff as ExportOptions).format}`);
  }
}

/** 渲染并写入文件,返回输出路径。 */
export async function exportToFile(
  input: ExportInput,
  opts: ExportOptions,
  outPath: string,
): Promise<string> {
  const data = await exportToBuffer(input, opts);
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, data);
  return outPath;
}

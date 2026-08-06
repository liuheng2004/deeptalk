import type { ExportInput, ExportOptions } from './types.js';

/** 默认隐藏的占位昵称。 */
export const ANONYMOUS_PEER = '匿名';

/**
 * 隐私默认策略:敏感字段(对方昵称 / 深度评分)默认隐藏。
 * - 昵称:开启 showSensitive 时显示真实昵称,否则显示「匿名」。
 * - 评分:仅当 showSensitive 为 true 时才允许外露。
 */
export function peerLabel(input: ExportInput, opts: ExportOptions): string {
  return opts.showSensitive ? input.session.peer : ANONYMOUS_PEER;
}

/** 是否允许外露深度评分。 */
export function scoreVisible(opts: ExportOptions): boolean {
  return opts.showSensitive === true;
}

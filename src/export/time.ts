import type { AnalysisResult, TimeInfo } from './types.js';

const WEEKDAYS = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];

function pad(n: number): string {
  return n < 10 ? '0' + n : String(n);
}

/** 日期 + 星期:2024年5月20日 星期一 */
export function formatDateLabel(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${WEEKDAYS[d.getDay()]}`;
}

/** 时钟:22:13 */
export function formatClock(iso: string): string {
  const d = new Date(iso);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** 时长:1小时34分钟 / 34分钟 / 2小时 */
export function formatDuration(minutes: number): string {
  const m = Math.max(0, Math.round(minutes));
  const h = Math.floor(m / 60);
  const rem = m % 60;
  if (h === 0) return `${rem}分钟`;
  if (rem === 0) return `${h}小时`;
  return `${h}小时${rem}分钟`;
}

/** 距今:2年前的今天 / 约2年前 / 约3个月前 / 约12天前 / 就在今天 */
export function formatSince(fromISO: string, now: Date = new Date()): string {
  const from = new Date(fromISO);
  const years = now.getFullYear() - from.getFullYear();
  const sameMonthDay = now.getMonth() === from.getMonth() && now.getDate() === from.getDate();

  if (years === 0 && now.getTime() - from.getTime() < 86_400_000) {
    return '就在今天';
  }
  if (years > 0 && sameMonthDay) {
    return `${years}年前的今天`;
  }

  const days = Math.floor((now.getTime() - from.getTime()) / 86_400_000);
  if (days < 30) return `约${days}天前`;
  const months = Math.floor(days / 30);
  if (months < 12) return `约${months}个月前`;
  return `约${years}年前`;
}

/** 由起止时间估算时长(分钟),供 duration_minutes 缺失时兜底。 */
function estimateDuration(startISO: string, endISO: string): number {
  const ms = new Date(endISO).getTime() - new Date(startISO).getTime();
  return Math.max(0, ms / 60_000);
}

/** 汇总一次导出的全部时间标注。 */
export function buildTimeInfo(analysis: AnalysisResult, now?: Date): TimeInfo {
  const duration = analysis.duration_minutes ?? estimateDuration(analysis.start_time, analysis.end_time);
  return {
    dateLabel: formatDateLabel(analysis.start_time),
    startTimeLabel: formatClock(analysis.start_time),
    endTimeLabel: formatClock(analysis.end_time),
    rangeLabel: `${formatClock(analysis.start_time)} - ${formatClock(analysis.end_time)}`,
    durationLabel: formatDuration(duration),
    sinceLabel: formatSince(analysis.start_time, now),
  };
}

import type { ExportInput, ExportOptions } from './types.js';
import { buildTimeInfo, formatClock } from './time.js';
import { peerLabel, scoreVisible } from './privacy.js';
import { buildTitle } from './title.js';

function yamlString(value: string): string {
  return JSON.stringify(value);
}

/** 渲染 Markdown 可迁移笔记(YAML front matter + 正文)。 */
export function renderMarkdown(input: ExportInput, opts: ExportOptions): string {
  const brand = opts.brand ?? 'DeepTalk';
  const title = buildTitle(input, opts);
  const a = input.analysis;
  const time = buildTimeInfo(a);

  const lines: string[] = [];

  // —— YAML front matter(便于 Obsidian 检索)——
  lines.push('---');
  lines.push(`title: ${yamlString(title)}`);
  lines.push(`date: ${a.start_time.slice(0, 10)}`);
  if (scoreVisible(opts)) {
    lines.push(`peer: ${yamlString(input.session.peer)}`);
    lines.push(`depth_score: ${a.depth_score}`);
  } else {
    lines.push(`peer: ${yamlString('匿名')}`);
  }
  lines.push(`tags: [${a.tags.map(yamlString).join(', ')}]`);
  lines.push(`session_id: ${input.session.session_id}`);
  lines.push(`segment_id: ${a.segment_id}`);
  if (a.model) lines.push(`model: ${yamlString(a.model)}`);
  lines.push(`source: ${yamlString(brand)}`);
  lines.push('---');
  lines.push('');

  // —— 正文 ——
  lines.push(`# ${title}`);
  lines.push('');
  lines.push(
    `> ${time.dateLabel} · ${time.rangeLabel} · 时长 ${time.durationLabel} · ${time.sinceLabel}`,
  );
  lines.push('');
  lines.push(`- 对话对象:${peerLabel(input, opts)}`);
  if (scoreVisible(opts)) lines.push(`- 深度评分:${a.depth_score}`);
  if (a.dimensions) {
    const d = a.dimensions;
    lines.push(
      `- 四维评分:情感 ${d.emotion} / 事件 ${d.event} / 连续 ${d.continuity} / 互动 ${d.interaction}`,
    );
  }
  lines.push(`- 标签:${a.tags.join('、') || '（无）'}`);
  lines.push('');

  lines.push('## 对话摘要');
  lines.push('');
  lines.push(a.summary);
  lines.push('');

  lines.push('## AI 第三方回应');
  lines.push('');
  lines.push(input.aiResponse ?? '（暂无）');
  lines.push('');

  lines.push('## 完整对话');
  lines.push('');
  for (const m of a.messages) {
    const who = m.sender === 'me' ? '我' : scoreVisible(opts) ? m.sender : '对方';
    lines.push(`**${who}** _(${formatClock(m.timestamp)})_: ${m.content}`);
    lines.push('');
  }

  return lines.join('\n');
}

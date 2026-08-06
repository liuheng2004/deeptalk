import * as pureimage from 'pureimage';
import { Writable } from 'node:stream';
import type { ExportInput, ExportOptions } from './types.js';
import { resolveCjkFont } from './fonts.js';
import { buildTimeInfo } from './time.js';
import { peerLabel, scoreVisible } from './privacy.js';

const CJK_FAMILY = 'cjk';
const W = 1080;
const H = 1440;

/** 已加载字体的缓存,避免重复解析。 */
const loadedFonts = new Set<string>();
function ensureFont(path: string): void {
  if (loadedFonts.has(path)) return;
  pureimage.registerFont(path, CJK_FAMILY).loadSync();
  loadedFonts.add(path);
}

/** 在 maxWidth 内按字符折行(中文逐字、保留拉丁单词完整性)。 */
function wrapText(ctx: any, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  let line = '';
  for (const raw of text.split(/(\s+)/)) {
    const token = raw;
    if (token === '') continue;
    if (/^\s+$/.test(token)) {
      line += ' ';
      continue;
    }
    let buf = '';
    for (const ch of token) {
      const test = line + buf + ch;
      if (ctx.measureText(test).width > maxWidth && (line + buf).trim().length > 0) {
        lines.push((line + buf).trimEnd());
        line = '';
        buf = ch;
      } else {
        buf += ch;
      }
    }
    line += buf;
  }
  if (line.trim().length > 0) lines.push(line.trimEnd());
  return lines.length ? lines : [''];
}

function encodeToBuffer(canvas: any): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    const sink = new Writable({
      write(chunk, _enc, cb) {
        chunks.push(chunk);
        cb();
      },
    });
    sink.on('finish', () => resolve(Buffer.concat(chunks)));
    sink.on('error', reject);
    pureimage.encodePNGToStream(canvas, sink).catch(reject);
  });
}

/** 渲染 PNG 分享卡片(1080×1440,朋友圈友好 3:4)。 */
export async function renderPng(input: ExportInput, opts: ExportOptions): Promise<Buffer> {
  const fontPath = resolveCjkFont(opts.cjkFontPath);
  ensureFont(fontPath);

  const canvas = pureimage.make(W, H);
  const ctx = canvas.getContext('2d');

  const score = input.analysis.depth_score;
  const warm = score >= 70;
  const brand = opts.brand ?? 'DeepTalk';
  const time = buildTimeInfo(input.analysis);

  // 背景:由深度评分决定氛围色
  const bg = ctx.createLinearGradient(0, 0, 0, H);
  if (warm) {
    bg.addColorStop(0, '#FFE9C7');
    bg.addColorStop(1, '#FF9E6D');
  } else {
    bg.addColorStop(0, '#EEF1F5');
    bg.addColorStop(1, '#C7D0DB');
  }
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  ctx.textBaseline = 'top';
  ctx.textAlign = 'left';

  // 顶部:日期 + 距今
  ctx.fillStyle = 'rgba(40,40,40,0.85)';
  ctx.font = `42px ${CJK_FAMILY}`;
  ctx.fillText(time.dateLabel, 72, 84);
  ctx.fillStyle = 'rgba(40,40,40,0.6)';
  ctx.font = `32px ${CJK_FAMILY}`;
  ctx.fillText(time.sinceLabel, 72, 146);

  // 中部:主题标签(胶囊)+ 金句
  const tag = input.analysis.tags[0] ?? '';
  if (tag) {
    ctx.font = `34px ${CJK_FAMILY}`;
    const tagText = `# ${tag}`;
    const tagW = ctx.measureText(tagText).width;
    const padX = 24;
    const pillH = 64;
    const pillY = 250;
    ctx.fillStyle = warm ? 'rgba(255,255,255,0.55)' : 'rgba(255,255,255,0.7)';
    ctx.roundRect(72, pillY, tagW + padX * 2, pillH, pillH / 2);
    ctx.fill();
    ctx.fillStyle = warm ? 'rgba(120,60,10,0.9)' : 'rgba(40,60,90,0.9)';
    ctx.fillText(tagText, 72 + padX, pillY + (pillH - 34) / 2);
  }

  const quoteSize = 52;
  let y = 360;
  ctx.fillStyle = 'rgba(20,20,20,0.92)';
  const quotes = input.analysis.golden_quotes.slice(0, 2);
  for (const q of quotes) {
    ctx.font = `${quoteSize}px ${CJK_FAMILY}`;
    const lines = wrapText(ctx, `“${q.text}”`, W - 144);
    for (const ln of lines) {
      ctx.fillText(ln, 72, y);
      y += quoteSize + 18;
    }
    y += 20;
  }

  // 底部:对方昵称(可隐藏)+ 深度评分(可隐藏)
  const by = H - 168;
  ctx.font = `40px ${CJK_FAMILY}`;
  ctx.fillStyle = 'rgba(20,20,20,0.9)';
  ctx.fillText(`对话对象:${peerLabel(input, opts)}`, 72, by);
  if (scoreVisible(opts)) {
    ctx.fillText(`深度评分:${score}`, 72, by + 56);
  }

  // 右下角半透明品牌水印(可关闭)
  if (opts.watermark !== false) {
    ctx.textAlign = 'right';
    ctx.textBaseline = 'alphabetic';
    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.font = `36px ${CJK_FAMILY}`;
    ctx.fillText(brand, W - 56, H - 56);
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
  }

  return encodeToBuffer(canvas);
}

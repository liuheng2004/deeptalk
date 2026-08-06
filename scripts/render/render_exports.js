#!/usr/bin/env node
// DeepTalk 导出渲染器:读入 JSON,输出分享卡片 PNG 与归档 PDF。
// 用法:node render_exports.js <input.json>
'use strict';

const fs = require('fs');
const pureimage = require('pureimage');
const PDFDocument = require('pdfkit');

const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const FONT = data.font || 'C:/Windows/Fonts/simhei.ttf';
const W = 1080, H = 1440;

function fmtDate(iso) {
  if (!iso) return '';
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? m[1] + '.' + m[2] + '.' + m[3] : iso;
}

function wrap(ctx, text, maxWidth) {
  const lines = [];
  let cur = '';
  for (const ch of text) {
    if (ch === '\n') { lines.push(cur); cur = ''; continue; }
    const w = ctx.measureText(cur + ch).width;
    if (w > maxWidth && cur) { lines.push(cur); cur = ch; }
    else cur += ch;
  }
  if (cur || lines.length === 0) lines.push(cur);
  return lines;
}

function makeGradient(ctx, score) {
  let top, bottom;
  if (score >= 80) { top = [72, 54, 60]; bottom = [38, 28, 40]; }
  else if (score >= 60) { top = [46, 44, 66]; bottom = [24, 22, 38]; }
  else { top = [58, 58, 62]; bottom = [30, 30, 34]; }
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, 'rgb(' + top.join(',') + ')');
  grad.addColorStop(1, 'rgb(' + bottom.join(',') + ')');
  return grad;
}

async function renderPNG() {
  const font = pureimage.registerFont(FONT, 'cjk');
  font.loadSync();
  const canvas = pureimage.make(W, H);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = makeGradient(ctx, data.depth_score);
  ctx.fillRect(0, 0, W, H);

  const white = '#faf8f5';
  const muted = '#cdc6c3';
  const accent = '#f0c878';

  ctx.font = '34px cjk';
  ctx.fillStyle = muted;
  const dateLine = (data.date_text || fmtDate(data.start_time)) +
    (data.relative_text ? ' · ' + data.relative_text : '');
  ctx.fillText(dateLine, 90, 120);

  ctx.font = '92px cjk';
  ctx.fillStyle = white;
  ctx.fillText(data.title || '深度对话', 90, 210);

  ctx.strokeStyle = accent;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(90, 260);
  ctx.lineTo(330, 260);
  ctx.stroke();

  ctx.font = '34px cjk';
  ctx.fillStyle = accent;
  const tagText = (data.tags || []).join('  ');
  if (tagText) ctx.fillText(tagText, 90, 320);

  ctx.font = '62px cjk';
  ctx.fillStyle = white;
  let y = 430;
  for (const q of (data.golden_quotes || []).slice(0, 2)) {
    for (const line of wrap(ctx, '「' + q + '」', W - 180)) {
      ctx.fillText(line, 90, y);
      y += 92;
    }
  }

  const yb = H - 150;
  ctx.strokeStyle = 'rgba(255,255,255,0.25)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(90, yb - 40);
  ctx.lineTo(W - 90, yb - 40);
  ctx.stroke();

  ctx.font = '44px cjk';
  ctx.fillStyle = white;
  ctx.fillText('与 ' + (data.peer || '对方'), 90, yb);
  const scoreText = '深度评分 ' + Math.round(data.depth_score) + ' / 100';
  ctx.fillStyle = accent;
  const sw = ctx.measureText(scoreText).width;
  ctx.fillText(scoreText, W - 90 - sw, yb);

  ctx.font = '34px cjk';
  ctx.fillStyle = muted;
  ctx.fillText('DeepTalk 深度对话纪念', 90, yb + 70);
  const wm = ctx.measureText('DeepTalk').width;
  ctx.fillText('DeepTalk', W - 90 - wm, yb + 70);

  await pureimage.encodePNGToStream(canvas, fs.createWriteStream(data.out_png));
  console.log('PNG written:', data.out_png);
}

function renderPDF() {
  const doc = new PDFDocument({ size: 'A4', margin: 50 });
  const stream = fs.createWriteStream(data.out_pdf);
  doc.pipe(stream);

  doc.registerFont('cjk', FONT);
  doc.font('cjk');

  doc.fontSize(28).fillColor('#222222');
  doc.text('与' + (data.peer || '对方') + '的深度对话');
  doc.moveDown(0.5);
  doc.fontSize(12).fillColor('#666666');
  doc.text('对方: ' + (data.peer || '对方'));
  doc.text('时间: ' + fmtDate(data.start_time || data.created_at));
  doc.text('深度评分: ' + Math.round(data.depth_score) + ' / 100');
  doc.moveDown(1.2);

  doc.fontSize(18).fillColor('#111111');
  doc.text('对话摘要');
  doc.moveDown(0.3);
  doc.fontSize(12).fillColor('#333333');
  doc.text(data.summary || '');
  doc.moveDown(1);

  doc.fontSize(18).fillColor('#111111');
  doc.text('AI 第三方回应');
  doc.moveDown(0.3);
  doc.fontSize(12).fillColor('#333333');
  doc.text(data.response_text || '');
  doc.moveDown(1);

  doc.fontSize(18).fillColor('#111111');
  doc.text('完整对话');
  doc.moveDown(0.4);
  doc.fontSize(12).fillColor('#333333');
  for (const m of (data.messages || [])) {
    const sender = m.sender === 'me' ? '我' : (m.sender || '对方');
    doc.fontSize(10).fillColor('#888888');
    doc.text(sender + ' · ' + fmtDate(m.timestamp));
    doc.fontSize(12).fillColor('#333333');
    doc.text(m.content || '');
    doc.moveDown(0.4);
  }

  const range = doc.bufferedPageRange();
  for (let i = range.start; i < range.start + range.count; i++) {
    doc.switchToPage(i);
    doc.fontSize(9).fillColor('#aaaaaa');
    doc.text('DeepTalk · 第 ' + (i + 1) + ' 页', 50, 790, {
      width: 495, align: 'right'
    });
  }

  doc.end();
  stream.on('finish', () => console.log('PDF written:', data.out_pdf));
}

(async () => {
  if (data.out_png) await renderPNG();
  if (data.out_pdf) renderPDF();
})().catch((e) => { console.error('ERR', e); process.exit(1); });

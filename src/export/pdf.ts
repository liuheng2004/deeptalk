import PDFDocument from 'pdfkit';
import type { ExportInput, ExportOptions } from './types.js';
import { resolveCjkFont } from './fonts.js';
import { buildTimeInfo, formatClock } from './time.js';
import { peerLabel, scoreVisible } from './privacy.js';
import { buildTitle } from './title.js';

const MARGIN = 56;

interface CoverCtx {
  brand: string;
  title: string;
  input: ExportInput;
  opts: ExportOptions;
}

function drawCover(doc: PDFKit.PDFDocument, ctx: CoverCtx): void {
  const { brand, title, input, opts } = ctx;
  const time = buildTimeInfo(input.analysis);
  const pageW = doc.page.width;

  doc.y = 150;
  doc.fontSize(14).fillColor('#999999').text(brand, pageW / 2, doc.y, { align: 'center' });
  doc.moveDown(0.6);
  doc.fontSize(28).fillColor('#111111').text(title, { align: 'center' });
  doc.moveDown(1);
  doc.moveTo(MARGIN, doc.y).lineTo(pageW - MARGIN, doc.y).strokeColor('#dddddd').lineWidth(1).stroke();
  doc.moveDown(1.2);

  const lines = [
    time.dateLabel,
    `时间 ${time.rangeLabel}`,
    `时长 ${time.durationLabel}`,
    time.sinceLabel,
    `对话对象 ${peerLabel(input, opts)}`,
  ];
  if (scoreVisible(opts)) lines.push(`深度评分 ${input.analysis.depth_score}`);
  if (input.analysis.model) lines.push(`模型 ${input.analysis.model}`);

  doc.fontSize(13).fillColor('#444444');
  for (const l of lines) {
    doc.text(l, { align: 'center' });
    doc.moveDown(0.35);
  }
}

function sectionHeading(doc: PDFKit.PDFDocument, heading: string): void {
  doc.moveDown(0.6);
  doc.fontSize(16).fillColor('#111111').text(heading);
  doc.moveDown(0.3);
}

function drawFooter(doc: PDFKit.PDFDocument, brand: string, pageNo: number): void {
  const oldBottom = doc.page.margins.bottom;
  doc.page.margins.bottom = 0;
  const y = doc.page.height - 36;
  doc.fontSize(9).fillColor('#aaaaaa');
  doc.text(brand, MARGIN, y, { width: doc.page.width - MARGIN * 2, align: 'left' });
  doc.text(`第 ${pageNo} 页`, MARGIN, y, { width: doc.page.width - MARGIN * 2, align: 'right' });
  doc.page.margins.bottom = oldBottom;
}

/** 渲染 PDF 存档文档(A4,封面 + 摘要 + AI 回应 + 完整对话,页脚含品牌与页码)。 */
export function renderPdf(input: ExportInput, opts: ExportOptions): Promise<Buffer> {
  const fontPath = resolveCjkFont(opts.cjkFontPath);
  const brand = opts.brand ?? 'DeepTalk';
  const title = buildTitle(input, opts);

  const doc = new PDFDocument({
    size: 'A4',
    margin: MARGIN,
    bufferPages: true,
    info: { Title: title, Author: brand },
  });
  doc.registerFont('cjk', fontPath);
  doc.font('cjk');

  const chunks: Buffer[] = [];
  const done = new Promise<Buffer>((resolve, reject) => {
    doc.on('data', (c: Buffer) => chunks.push(c));
    doc.on('end', () => resolve(Buffer.concat(chunks)));
    doc.on('error', reject);
  });

  // 封面
  drawCover(doc, { brand, title, input, opts });
  // 内容另起一页,保证封面独立
  doc.addPage();

  // 对话摘要
  sectionHeading(doc, '对话摘要');
  doc.fontSize(12).fillColor('#222222').text(input.analysis.summary);
  doc.moveDown(0.6);

  // AI 第三方回应
  sectionHeading(doc, 'AI 第三方回应');
  doc.fontSize(12).fillColor('#222222').text(input.aiResponse ?? '（暂无）');
  doc.moveDown(0.6);

  // 完整对话
  sectionHeading(doc, '完整对话');
  for (const m of input.analysis.messages) {
    const who = m.sender === 'me' ? '我' : scoreVisible(opts) ? m.sender : '对方';
    doc.fontSize(11).fillColor('#777777').text(`${who} · ${formatClock(m.timestamp)}`);
    doc.fontSize(12).fillColor('#111111').text(m.content);
    doc.moveDown(0.5);
  }

  // 页脚:每页都带品牌小字 + 页码
  const range = doc.bufferedPageRange();
  for (let i = range.start; i < range.start + range.count; i++) {
    doc.switchToPage(i);
    drawFooter(doc, brand, i + 1);
  }
  doc.flushPages();
  doc.end();

  return done;
}

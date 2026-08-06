import { existsSync } from 'node:fs';

/**
 * 候选中文字体路径。按「显式指定 → 常见系统字体」的顺序探测,
 * 优先选择静态 .ttf(SimHei),避免 .ttc 字体集合在部分渲染库下的兼容问题。
 */
const CANDIDATES: string[] = [
  process.env.DEEPTALK_CJK_FONT ?? '',
  'C:/Windows/Fonts/simhei.ttf',
  'C:/Windows/Fonts/msyh.ttc',
  'C:/Windows/Fonts/NotoSansSC-VF.ttf',
  '/System/Library/Fonts/PingFang.ttc',
  '/Library/Fonts/Arial Unicode.ttf',
  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
  '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttf',
].filter(Boolean);

/** 解析一个可用的中文字体路径;找不到时抛出明确错误。 */
export function resolveCjkFont(explicit?: string): string {
  const list = [explicit, ...CANDIDATES].filter(Boolean) as string[];
  for (const p of list) {
    if (existsSync(p)) return p;
  }
  throw new Error(
    '未找到可用的中文字体。请通过 options.cjkFontPath 或环境变量 DEEPTALK_CJK_FONT 指定一个 CJK 字体文件(.ttf/.otf)的路径。',
  );
}

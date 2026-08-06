import { statSync } from 'node:fs';
import { exportToFile } from './index.js';
import type { ChatMessage, ExportInput, ExportOptions } from './types.js';

/** 生成本机时区的 ISO(不带 Z),保证渲染出来的时钟与样例数据一致。 */
function localISO(d: Date): string {
  const off = d.getTimezoneOffset();
  const local = new Date(d.getTime() - off * 60_000);
  return local.toISOString().slice(0, 16);
}

function msg(id: string, sender: string, content: string, h: number, m: number): ChatMessage {
  return {
    id,
    sender,
    content,
    type: 'text',
    timestamp: localISO(new Date(2024, 4, 20, h, m)),
  };
}

const input: ExportInput = {
  session: {
    session_id: 'sess-xiaoman-20240520',
    peer: '小满',
    created_at: localISO(new Date(2024, 4, 20, 22, 13)),
    source: 'wechat-email-txt',
    messages: [
      msg('m1', 'me', '这么晚了还没睡?', 22, 13),
      msg('m2', '小满', '嗯,刚把离职的念头又翻出来想了一遍。', 22, 15),
      msg('m3', 'me', '是那份做了三年、越来越觉得不是自己的方向的工作吗?', 22, 17),
      msg('m4', '小满', '对。身边人都说稳定多好,可我每天醒来都在想,如果再过五年还是这样怎么办。', 22, 21),
      msg('m5', 'me', '你怕的其实不是不稳定,是「把人生交出去」吧。', 22, 25),
      msg('m6', '小满', '……你这句话戳到我了。我妈那辈人觉得安稳就是孝顺,可我好像一直在替别人活。', 22, 30),
      msg('m7', 'me', '那如果抛开所有人期待,你真正想试的一件事是什么?', 22, 38),
      msg('m8', '小满', '开一间小小的植物工作室,哪怕先周末摆摊。说出来都觉得奢侈。', 22, 44),
      msg('m9', 'me', '奢侈才值得。要不这周末先去花鸟市场转一圈,就当探路?', 22, 50),
      msg('m10', '小满', '好。谢谢你今晚听我说这些,我好像没那么怕了。', 23, 2),
    ],
    note: '时间戳由微信邮件导出的首尾消息推断。',
  },
  analysis: {
    segment_id: 'seg-20240520-xiaoman',
    session_id: 'sess-xiaoman-20240520',
    depth_score: 87,
    threshold: 60,
    is_deep: true,
    dimensions: { emotion: 92, event: 78, continuity: 84, interaction: 88 },
    start_time: localISO(new Date(2024, 4, 20, 22, 13)),
    end_time: localISO(new Date(2024, 4, 20, 23, 47)),
    duration_minutes: 94,
    summary:
      '小满在深夜向「我」坦白想离开做了三年的稳定工作。她真正恐惧的是把人生交到别人期待里,而非不稳定本身。两人聊到她一直想开一间植物工作室,并最终约定这周末先去花鸟市场探路。',
    tags: ['深夜emo', '职业选择'],
    golden_quotes: [
      { text: '你怕的其实不是不稳定,是「把人生交出去」吧。', message_id: 'm5' },
      { text: '我好像一直在替别人活。', message_id: 'm6' },
    ],
    messages: [
      msg('m1', 'me', '这么晚了还没睡?', 22, 13),
      msg('m2', '小满', '嗯,刚把离职的念头又翻出来想了一遍。', 22, 15),
      msg('m3', 'me', '是那份做了三年、越来越觉得不是自己的方向的工作吗?', 22, 17),
      msg('m4', '小满', '对。身边人都说稳定多好,可我每天醒来都在想,如果再过五年还是这样怎么办。', 22, 21),
      msg('m5', 'me', '你怕的其实不是不稳定,是「把人生交出去」吧。', 22, 25),
      msg('m6', '小满', '……你这句话戳到我了。我妈那辈人觉得安稳就是孝顺,可我好像一直在替别人活。', 22, 30),
      msg('m7', 'me', '那如果抛开所有人期待,你真正想试的一件事是什么?', 22, 38),
      msg('m8', '小满', '开一间小小的植物工作室,哪怕先周末摆摊。说出来都觉得奢侈。', 22, 44),
      msg('m9', 'me', '奢侈才值得。要不这周末先去花鸟市场转一圈,就当探路?', 22, 50),
      msg('m10', '小满', '好。谢谢你今晚听我说这些,我好像没那么怕了。', 23, 2),
    ],
    model: 'deepseek-v4-flash',
  },
  aiResponse:
    '小满的犹豫里藏着很清醒的东西——她不是冲动想逃,而是终于听清了自己一直在替谁活。你那句「把人生交出去」点得很准:真正让人害怕的从来不是不确定,而是把选择权让渡出去后的空。她愿意从「周末摆摊探路」这种很低成本的方式开始,其实已经把恐惧拆成了可执行的下一步。接下来值得陪她把「植物工作室」从念头变成一张具体的清单:成本、时间、最坏结果分别是什么。',
};

async function main(): Promise<void> {
  const outDir = 'samples';
  const jobs: Array<[ExportOptions, string, string]> = [
    // 三份验收样例(默认:水印开、敏感字段隐藏)
    [{ format: 'png' }, `${outDir}/deeptalk-sample.png`, 'PNG'],
    [{ format: 'pdf' }, `${outDir}/deeptalk-sample.pdf`, 'PDF'],
    [{ format: 'md' }, `${outDir}/deeptalk-sample.md`, 'MD'],
    // 演示开关:显示敏感字段(昵称 + 评分)
    [{ format: 'png', showSensitive: true }, `${outDir}/deeptalk-sample.sensitive.png`, 'PNG(显示敏感字段)'],
    // 演示开关:关闭水印
    [{ format: 'png', watermark: false }, `${outDir}/deeptalk-sample.nowatermark.png`, 'PNG(无水印)'],
  ];

  for (const [opts, file, label] of jobs) {
    const path = await exportToFile(input, opts, file);
    const size = statSync(path).size;
    console.log(`✓ ${label.padEnd(18)} -> ${path} (${size} bytes)`);
  }
  console.log('\n样例生成完成。');
}

main().catch((err) => {
  console.error('样例生成失败:', err);
  process.exit(1);
});

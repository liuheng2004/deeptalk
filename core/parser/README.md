# core/parser

微信 txt 导入解析:解析官方「邮件发送聊天记录」导出文件 → 符合 `docs/contracts/session.schema.json` 的会话模型。

- `wechat.py`:微信官方 txt 解析(时间戳推断、昵称识别、清洗去重)。
- `ocr.py`:AI 聊天截图导入(豆包 / ChatGPT / DeepSeek 等左右气泡布局),本地 RapidOCR
  提取文本 → 按气泡分组识别说话人 → 会话模型;只存文本不存图。

OCR 用法:

    .venv/Scripts/python -m core.parser.ocr a.png b.png --peer AI --me-side right

负责人:ArkAgent(glm)+ Codex。

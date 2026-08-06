// 导入页 —— 微信「邮件发送聊天记录」导出的 txt(纯文本)。
// 演示:粘贴 / 拖入文本后「解析」,加载符合 session.schema.json 的会话,
// 并进入卡片流。真实解析由 core/parser 负责(本任务仅做前端 UI)。
import { SESSION_FIELDS, MESSAGE_FIELDS } from "../contracts.js";
import { SAMPLE_SESSION, SAMPLE_ANALYSES } from "../data.js";
import { importSession, loadSample } from "../store.js";
import { escapeHtml } from "../util.js";

const SAMPLE_TXT = `林夕 22:01
你最近睡得还好吗?
林夕 22:01
不太好,总在想以后的事。
我 22:02
说给我听听。
林夕 22:03
怕选错路,又怕原地踏步。`;

export function mount(root) {
  const sessionReq = SESSION_FIELDS.filter((f) => f.required)
    .map((f) => `<li><code>${f.key}</code> <span>${escapeHtml(f.label)}</span> <span class="req">必填</span></li>`)
    .join("");
  const messageReq = MESSAGE_FIELDS.filter((f) => f.required)
    .map((f) => `<li><code>${f.key}</code> <span>${escapeHtml(f.label)}</span> <span class="req">必填</span></li>`)
    .join("");

  root.innerHTML = `
  <section class="page-head">
    <h1>导入聊天记录</h1>
    <p>支持微信官方「邮件发送聊天记录」导出的 txt(纯文本,图片不导入)。</p>
  </section>

  <div class="dropzone" id="drop">
    <p>把 .txt 文件拖到这里,或直接在下方粘贴内容</p>
  </div>

  <div class="panel" style="margin-top:16px">
    <textarea class="paste" id="txt" placeholder="在此粘贴微信导出的聊天文本…">${escapeHtml(SAMPLE_TXT)}</textarea>
    <div class="btn-row" style="margin-top:14px">
      <button class="btn" id="parse">解析并进入卡片流</button>
      <button class="btn secondary" id="useSample">载入示例会话</button>
    </div>
    <p class="small muted" style="margin-top:10px">
      注:真实解析由 <code>core/parser</code> 产出 <code>session.schema.json</code>;本页仅做前端演示,
      点击任一按钮均加载符合契约的示例会话。
    </p>
  </div>

  <div class="panel" style="margin-top:16px">
    <h3 style="margin-top:0">导入产出的契约字段(与 docs/contracts 对应)</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
      <div>
        <h4 class="muted">ChatSession 必填</h4>
        <ul class="field-list">${sessionReq}</ul>
      </div>
      <div>
        <h4 class="muted">message 必填</h4>
        <ul class="field-list">${messageReq}</ul>
      </div>
    </div>
  </div>`;

  const txt = root.querySelector("#txt");
  const drop = root.querySelector("#drop");

  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("drag"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault(); drop.classList.remove("drag");
    const file = e.dataTransfer.files?.[0];
    if (file) {
      const r = new FileReader();
      r.onload = () => { txt.value = r.result; };
      r.readAsText(file);
    }
  });

  function go() {
    if (!txt.value.trim()) {
      alert("请先粘贴或拖入聊天文本。");
      return;
    }
    // 演示:以示例会话填充契约结构(core/parser 的等价产出)
    importSession({ session: SAMPLE_SESSION, analyses: SAMPLE_ANALYSES });
    location.hash = "#/";
  }

  root.querySelector("#parse").addEventListener("click", go);
  root.querySelector("#useSample").addEventListener("click", () => {
    loadSample();
    location.hash = "#/";
  });
}

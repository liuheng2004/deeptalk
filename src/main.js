import { invoke } from "@tauri-apps/api/core";

const statusEl = document.getElementById("status");
const cardsEl = document.getElementById("cards");

function renderCards(sessions) {
  cardsEl.innerHTML = "";
  if (!sessions || sessions.length === 0) {
    cardsEl.innerHTML = "<li class='empty'>暂无数据 — 点击「导入会话(占位)」写入一条加密样例</li>";
    return;
  }
  for (const s of sessions) {
    const li = document.createElement("li");
    li.className = "card";
    li.innerHTML = `
      <div class="card-title">${escapeHtml(s.peer)}</div>
      <div class="card-meta">${escapeHtml(s.created_at || "")} · ${s.message_count ?? 0} 条消息</div>
    `;
    cardsEl.appendChild(li);
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

async function refresh() {
  try {
    const sessions = await invoke("list_cards");
    renderCards(sessions);
    statusEl.textContent = `已加载 ${sessions.length} 个会话`;
  } catch (err) {
    statusEl.textContent = `读取失败: ${err}`;
  }
}

document.getElementById("btn-import").addEventListener("click", async () => {
  const sample = {
    session_id: "sample-" + Date.now(),
    peer: "星河",
    created_at: new Date().toISOString(),
    source: "wechat-email-txt",
    messages: [
      {
        id: "m1",
        sender: "me",
        content: "今晚聊得真开心",
        type: "text",
        timestamp: new Date().toISOString(),
      },
      {
        id: "m2",
        sender: "星河",
        content: "我也是,很久没有这样说过话了",
        type: "text",
        timestamp: new Date().toISOString(),
      },
    ],
  };
  try {
    const sessionId = await invoke("import_session", { session: sample });
    statusEl.textContent = `已导入并加密存储: ${sessionId}`;
    await refresh();
  } catch (err) {
    statusEl.textContent = `导入失败: ${err}`;
  }
});

refresh();

//! Tauri command 层:导入会话、查询卡片(骨架,字段与 docs/contracts 对齐)。

use crate::{AppState, crypto::Cipher};
use serde_json::{Value, json};
use std::sync::MutexGuard;
use tauri::State;

fn cipher<'a>(state: &'a AppState) -> &'a Cipher {
    &state.cipher
}

fn db<'a>(state: &'a AppState) -> MutexGuard<'a, crate::db::Database> {
    state.db.lock().expect("db lock poisoned")
}

/// 导入一个符合 session.schema.json 的会话(内容字段加密后落盘)。
#[tauri::command]
pub fn import_session(state: State<AppState>, session: Value) -> Result<String, String> {
    let session_id = session
        .get("session_id")
        .and_then(Value::as_str)
        .ok_or("missing session_id")?
        .to_string();
    let peer = session
        .get("peer")
        .and_then(Value::as_str)
        .unwrap_or("");
    let created_at = session
        .get("created_at")
        .and_then(Value::as_str)
        .unwrap_or("");
    let source = session.get("source").and_then(Value::as_str);
    let note = session.get("note").and_then(Value::as_str);
    let messages = session
        .get("messages")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();

    let c = cipher(&state);
    let peer_enc = c.encrypt(peer)?;
    let db = db(&state);
    db.insert_session(
        &session_id,
        &peer_enc,
        created_at,
        None,
        source,
        messages.len() as i64,
        note,
    )?;

    for msg in &messages {
        let id = msg.get("id").and_then(Value::as_str).unwrap_or("");
        let sender = msg.get("sender").and_then(Value::as_str).unwrap_or("");
        let content = msg.get("content").and_then(Value::as_str).unwrap_or("");
        let msg_type = msg.get("type").and_then(Value::as_str).unwrap_or("text");
        let timestamp = msg.get("timestamp").and_then(Value::as_str);
        let inferred = msg
            .get("inferred_time")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let quote_of = msg.get("quote_of").and_then(Value::as_str);

        let sender_enc = c.encrypt(sender)?;
        let content_enc = c.encrypt(content)?;
        db.insert_message(
            id,
            &session_id,
            &sender_enc,
            &content_enc,
            msg_type,
            timestamp,
            inferred,
            quote_of,
        )?;
    }

    log::info!(
        "imported session {} ({} messages)",
        session_id,
        messages.len()
    );
    Ok(session_id)
}

/// 查询已存储会话(骨架;识别卡片在 M1-2 之后接入)。
#[tauri::command]
pub fn list_cards(state: State<AppState>) -> Result<Vec<Value>, String> {
    let c = cipher(&state);
    let db = db(&state);
    let sessions = db.list_sessions()?;
    let mut out = Vec::new();
    for (session_id, peer_enc, created_at, message_count) in sessions {
        let peer = c.decrypt(&peer_enc)?;
        out.push(json!({
            "session_id": session_id,
            "peer": peer,
            "created_at": created_at,
            "message_count": message_count,
        }));
    }
    Ok(out)
}

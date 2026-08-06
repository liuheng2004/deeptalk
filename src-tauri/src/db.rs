//! 本地 SQLite 存储(敏感内容字段以密文落盘,由 crypto::Cipher 加解密)。

use rusqlite::{params, Connection};
use std::path::PathBuf;

pub struct Database {
    conn: Connection,
}

fn db_path() -> PathBuf {
    dirs::data_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("deeptalk")
        .join("deeptalk.db")
}

impl Database {
    pub fn open() -> Result<Self, String> {
        let path = db_path();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        let conn = Connection::open(&path).map_err(|e| e.to_string())?;
        conn.execute_batch(
            r#"
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                peer TEXT NOT NULL,            -- 加密
                created_at TEXT NOT NULL,
                updated_at TEXT,
                source TEXT,
                message_count INTEGER DEFAULT 0,
                note TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL,          -- 加密
                content TEXT NOT NULL,         -- 加密
                type TEXT DEFAULT 'text',
                timestamp TEXT,
                inferred_time INTEGER DEFAULT 0,
                quote_of TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            "#,
        )
        .map_err(|e| e.to_string())?;
        Ok(Self { conn })
    }

    pub fn insert_session(
        &self,
        session_id: &str,
        peer_enc: &str,
        created_at: &str,
        updated_at: Option<&str>,
        source: Option<&str>,
        message_count: i64,
        note: Option<&str>,
    ) -> Result<(), String> {
        self.conn
            .execute(
                "INSERT OR REPLACE INTO sessions
                 (session_id, peer, created_at, updated_at, source, message_count, note)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                params![
                    session_id,
                    peer_enc,
                    created_at,
                    updated_at,
                    source,
                    message_count,
                    note
                ],
            )
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn insert_message(
        &self,
        id: &str,
        session_id: &str,
        sender_enc: &str,
        content_enc: &str,
        msg_type: &str,
        timestamp: Option<&str>,
        inferred_time: bool,
        quote_of: Option<&str>,
    ) -> Result<(), String> {
        self.conn
            .execute(
                "INSERT OR REPLACE INTO messages
                 (id, session_id, sender, content, type, timestamp, inferred_time, quote_of)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
                params![
                    id,
                    session_id,
                    sender_enc,
                    content_enc,
                    msg_type,
                    timestamp,
                    inferred_time as i64,
                    quote_of
                ],
            )
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn list_sessions(&self) -> Result<Vec<(String, String, String, i64)>, String> {
        let mut stmt = self
            .conn
            .prepare(
                "SELECT session_id, peer, created_at, message_count
                 FROM sessions ORDER BY created_at DESC",
            )
            .map_err(|e| e.to_string())?;
        let rows = stmt
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, i64>(3)?,
                ))
            })
            .map_err(|e| e.to_string())?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row.map_err(|e| e.to_string())?);
        }
        Ok(out)
    }
}

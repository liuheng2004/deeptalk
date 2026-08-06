//! DeepTalk 桌面端骨架 (M1-3)
//!
//! 职责:窗口管理、本地加密存储(SQLite + AES-256-GCM)、配置、日志。
//! 后续模块(core/parser、core/analysis)通过 Tauri command 接入。

mod commands;
mod config;
mod crypto;
mod db;

use std::sync::Mutex;
use tauri::Manager;

pub struct AppState {
    pub cipher: crypto::Cipher,
    pub db: Mutex<db::Database>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let config = config::load();
    log::info!(
        "DeepTalk starting (model={}, watermark={})",
        config.model,
        config.watermark
    );

    let cipher = crypto::Cipher::load_or_create().expect("failed to init cipher");
    let database = db::Database::open().expect("failed to open database");
    let state = AppState {
        cipher,
        db: Mutex::new(database),
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(state)
        .invoke_handler(tauri::generate_handler![
            commands::import_session,
            commands::list_cards
        ])
        .setup(|app| {
            let dir = app
                .path()
                .app_data_dir()
                .expect("app data dir unavailable");
            log::info!("data dir: {}", dir.display());
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

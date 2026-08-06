//! 本地加密:AES-256-GCM。
//!
//! 主密钥:首次运行生成 32 字节随机密钥,保存在应用数据目录
//! `deeptalk/master.key`(本机文件权限保护;OS 钥匙串集成列入 P2)。
//! 也可用环境变量 `DEEPTALK_MASTER_KEY`(64 位 hex)覆盖。

use aes_gcm::aead::{Aead, KeyInit, OsRng};
use aes_gcm::{Aes256Gcm, Nonce};
use rand::RngCore;
use std::fs;
use std::path::PathBuf;

pub struct Cipher {
    cipher: Aes256Gcm,
}

fn key_path() -> PathBuf {
    let dir = dirs::data_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("deeptalk");
    dir.join("master.key")
}

impl Cipher {
    pub fn load_or_create() -> Result<Self, String> {
        let key = if let Ok(hex_key) = std::env::var("DEEPTALK_MASTER_KEY") {
            hex_decode(&hex_key)?
        } else {
            let path = key_path();
            if path.exists() {
                let hex = fs::read_to_string(&path).map_err(|e| e.to_string())?;
                hex_decode(hex.trim())?
            } else {
                let mut key = [0u8; 32];
                OsRng.fill_bytes(&mut key);
                if let Some(parent) = path.parent() {
                    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
                }
                fs::write(&path, hex_encode(&key)).map_err(|e| e.to_string())?;
                key
            }
        };
        Ok(Self {
            cipher: Aes256Gcm::new_from_slice(&key).map_err(|e| e.to_string())?,
        })
    }

    pub fn encrypt(&self, plain: &str) -> Result<String, String> {
        let mut nonce_bytes = [0u8; 12];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);
        let ct = self
            .cipher
            .encrypt(nonce, plain.as_bytes())
            .map_err(|e| e.to_string())?;
        Ok(format!(
            "v1:{}:{}",
            hex_encode(&nonce_bytes),
            hex_encode(&ct)
        ))
    }

    pub fn decrypt(&self, blob: &str) -> Result<String, String> {
        let parts: Vec<&str> = blob.splitn(3, ':').collect();
        if parts.len() != 3 || parts[0] != "v1" {
            return Err("unsupported ciphertext format".to_string());
        }
        let nonce_bytes = hex_decode(parts[1])?;
        let ct = hex_decode(parts[2])?;
        let pt = self
            .cipher
            .decrypt(Nonce::from_slice(&nonce_bytes), ct.as_slice())
            .map_err(|e| e.to_string())?;
        String::from_utf8(pt).map_err(|e| e.to_string())
    }
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

fn hex_decode(hex: &str) -> Result<Vec<u8>, String> {
    if hex.len() % 2 != 0 {
        return Err("invalid hex length".to_string());
    }
    (0..hex.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&hex[i..i + 2], 16).map_err(|e| e.to_string()))
        .collect()
}

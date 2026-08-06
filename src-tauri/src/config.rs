//! 配置加载:优先环境变量,回退读取仓库根目录的 .env(不提交密钥)。

use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Config {
    pub deepseek_api_key: String,
    pub deepseek_base_url: String,
    pub model: String,
}

fn parse_env_file(path: &Path) -> HashMap<String, String> {
    let mut map = HashMap::new();
    let Ok(content) = std::fs::read_to_string(path) else {
        return map;
    };
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if let Some((k, v)) = line.split_once('=') {
            map.insert(k.trim().to_string(), v.trim().to_string());
        }
    }
    map
}

pub fn load() -> Config {
    let mut env = parse_env_file(Path::new(".env"));
    for (k, v) in std::env::vars() {
        env.insert(k, v);
    }

    let get = |key: &str, default: &str| -> String {
        env.get(key).cloned().unwrap_or_else(|| default.to_string())
    };

    Config {
        deepseek_api_key: get("DEEPSEEK_API_KEY", ""),
        deepseek_base_url: get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model: get("DEEPTALK_MODEL", "deepseek-v4-flash"),
    }
}

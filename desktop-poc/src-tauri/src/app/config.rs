use serde_json::{json, Value};
use std::{collections::HashSet, fs, io::Write, path::PathBuf, sync::RwLock};

const DEFAULT_CONFIG: &str = include_str!("../../../default-config.json");

pub struct ConfigStore {
    path: PathBuf,
    current: RwLock<Value>,
}

impl ConfigStore {
    pub fn new(path: PathBuf) -> Result<Self, String> {
        if !path.exists() {
            write_private(&path, DEFAULT_CONFIG.as_bytes())?;
        }
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(&path, fs::Permissions::from_mode(0o600))
                .map_err(|e| e.to_string())?;
        }
        let raw: Value = serde_json::from_slice(&fs::read(&path).map_err(|e| e.to_string())?)
            .map_err(|e| format!("Invalid Rust configuration: {e}"))?;
        validate(&raw)?;
        Ok(Self {
            path,
            current: RwLock::new(raw),
        })
    }

    pub fn document(&self) -> Value {
        self.current.read().unwrap().clone()
    }

    pub fn feature_enabled(&self, name: &str) -> bool {
        self.current.read().unwrap()["features"][name]
            .as_bool()
            .unwrap_or(true)
    }

    pub fn poll_interval(&self) -> std::time::Duration {
        let seconds = self.current.read().unwrap()["server"]["poll_interval"]
            .as_f64()
            .unwrap_or(2.0)
            .clamp(0.2, 30.0);
        std::time::Duration::from_secs_f64(seconds)
    }

    pub fn volume_step(&self) -> u8 {
        self.current.read().unwrap()["server"]["volume_step"]
            .as_u64()
            .unwrap_or(5)
            .clamp(1, 50) as u8
    }

    pub fn save(&self, mut candidate: Value) -> Result<Value, String> {
        validate(&candidate)?;
        let mut current = self.current.write().unwrap();
        if candidate["server"]["token"]
            .as_str()
            .is_some_and(|token| !token.is_empty())
        {
            return Err("La sécurité par jeton partagé de l’ancien agent n’est pas encore disponible dans Tauri ; l’appairage individuel reste actif.".into());
        }
        if candidate["server"]["host"] != current["server"]["host"]
            || candidate["server"]["port"] != current["server"]["port"]
        {
            return Err(
                "Le changement de l’adresse réseau exige encore un redémarrage dans ce PoC.".into(),
            );
        }
        let old_revision = current["revision"].as_u64().unwrap_or(0);
        if candidate["revision"].as_u64() != Some(old_revision) {
            return Err("Configuration changed; reload before saving".into());
        }
        let disk: Value = serde_json::from_slice(&fs::read(&self.path).map_err(|e| e.to_string())?)
            .map_err(|e| format!("Configuration changed on disk: {e}"))?;
        if disk != *current {
            return Err("Configuration changed on disk; restart before saving".into());
        }
        candidate["revision"] = json!(old_revision + 1);
        let bytes = serde_json::to_vec_pretty(&candidate).map_err(|e| e.to_string())?;
        let temporary = self
            .path
            .with_extension(format!("{}.tmp", rand::random::<u64>()));
        write_private(&temporary, &bytes)?;
        if let Err(error) = fs::rename(&temporary, &self.path) {
            let _ = fs::remove_file(&temporary);
            return Err(error.to_string());
        }
        *current = candidate.clone();
        Ok(candidate)
    }

    pub fn snapshot(&self, locale: &str) -> Value {
        snapshot(&self.document(), locale)
    }

    pub fn resolve(&self, page: &str, button: &str, hold: bool) -> Option<Value> {
        let current = self.current.read().unwrap();
        let pages = current["pages"].as_array()?;
        let page = pages
            .iter()
            .find(|item| item["id"].as_str() == Some(page))?;
        let buttons = if page["layout"].as_str() == Some("list") {
            page["entries"].as_array()?
        } else {
            page["buttons"].as_array()?
        };
        let button = buttons
            .iter()
            .find(|item| item["id"].as_str() == Some(button))?;
        let action = if hold && !button["hold_action"].is_null() {
            &button["hold_action"]
        } else {
            &button["action"]
        };
        if action.is_null() {
            None
        } else {
            Some(action.clone())
        }
    }
}

fn write_private(path: &PathBuf, bytes: &[u8]) -> Result<(), String> {
    let mut options = fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(path).map_err(|e| e.to_string())?;
    file.write_all(bytes).map_err(|e| e.to_string())?;
    file.sync_all().map_err(|e| e.to_string())
}

fn localized(value: &Value, locale: &str, fallback: &str) -> String {
    if let Some(text) = value.as_str() {
        return text.to_string();
    }
    value
        .get(locale)
        .and_then(Value::as_str)
        .or_else(|| value.get("en").and_then(Value::as_str))
        .or_else(|| value.get("fr").and_then(Value::as_str))
        .unwrap_or(fallback)
        .to_string()
}

pub fn snapshot(config: &Value, locale: &str) -> Value {
    let pages = config["pages"].as_array().map(Vec::as_slice).unwrap_or(&[]);
    let pages: Vec<Value> = pages.iter().map(|page| {
        let mut payload = json!({
            "id": page["id"],
            "title": localized(&page["title"], locale, page["id"].as_str().unwrap_or("")),
            "icon": page.get("icon").unwrap_or(&Value::Null),
            "dashboard": page.get("dashboard").and_then(Value::as_str).unwrap_or("auto"),
            "layout": page.get("layout").and_then(Value::as_str).unwrap_or("grid"),
            "buttons": []
        });
        if page["layout"].as_str() == Some("list") {
            payload["entries"] = Value::Array(page["entries"].as_array().map(|items| items.iter().map(|entry| {
                let mut item = json!({"id":entry["id"],"label":localized(&entry["label"],locale,""),"icon":entry.get("icon").and_then(Value::as_str).unwrap_or("app"),"color":entry.get("color").and_then(Value::as_str).unwrap_or("#64748B")});
                if let Some(detail) = entry.get("detail").and_then(Value::as_str) { item["detail"] = json!(detail); }
                if entry["active"].as_bool() == Some(true) { item["active"] = json!(true); }
                item
            }).collect()).unwrap_or_default());
        } else {
            payload["buttons"] = Value::Array(page["buttons"].as_array().map(|buttons| buttons.iter().map(|button| {
                let mut item = json!({
                    "id": button["id"], "slot": button["slot"],
                    "label": localized(&button["label"], locale, ""),
                    "icon": button.get("icon").and_then(Value::as_str).unwrap_or("app"),
                    "color": button.get("color").and_then(Value::as_str).unwrap_or("#3B82F6")
                });
                if let Some(toggle) = button.get("toggle").and_then(Value::as_str) { item["toggle"] = json!(toggle); }
                if !button["hold_label"].is_null() { item["hold_label"] = json!(localized(&button["hold_label"],locale,"")); }
                item
            }).collect()).unwrap_or_default());
        }
        payload
    }).collect();
    json!({"type":"config.snapshot","revision":config["revision"],"pages":pages})
}

pub fn validate(raw: &Value) -> Result<(), String> {
    let revision = raw["revision"]
        .as_u64()
        .ok_or("revision must be a nonnegative integer")?;
    if revision == u64::MAX {
        return Err("revision too large".into());
    }
    if let Some(seconds) = raw["server"]["poll_interval"].as_f64() {
        if !(0.2..=30.0).contains(&seconds) {
            return Err("poll_interval must be between 0.2 and 30 seconds".into());
        }
    }
    if let Some(step) = raw["server"]["volume_step"].as_u64() {
        if !(1..=50).contains(&step) {
            return Err("volume_step must be between 1 and 50".into());
        }
    }
    if raw["integrations"]["obs"]["enabled"].as_bool() == Some(true) {
        crate::features::obs::ObsConfig::from_document(raw)?;
    }
    let pages = raw["pages"].as_array().ok_or("pages must be an array")?;
    if pages.is_empty() || pages.len() > 12 {
        return Err("pages must contain 1–12 entries".into());
    }
    let mut page_ids = HashSet::new();
    for page in pages {
        let id = valid_id(&page["id"], "page id")?;
        if !page_ids.insert(id) {
            return Err(format!("duplicate page id: {id}"));
        }
        valid_label(&page["title"], "page title")?;
        let layout = page["layout"].as_str().unwrap_or("grid");
        if !matches!(layout, "grid" | "list") {
            return Err(format!("invalid layout on page {id}"));
        }
        let buttons = page["buttons"]
            .as_array()
            .ok_or("buttons must be an array")?;
        if buttons.len() > 6 {
            return Err(format!("too many buttons on page {id}"));
        }
        let mut button_ids = HashSet::new();
        let mut slots = HashSet::new();
        for button in buttons {
            let button_id = valid_id(&button["id"], "button id")?;
            if !button_ids.insert(button_id) {
                return Err(format!("duplicate button id: {button_id}"));
            }
            let slot = button["slot"].as_u64().ok_or("slot must be an integer")?;
            if slot > 5 || !slots.insert(slot) {
                return Err(format!("invalid or duplicate slot on page {id}"));
            }
            valid_label(&button["label"], "button label")?;
            valid_action(&button["action"])?;
            if !button["hold_action"].is_null() {
                valid_action(&button["hold_action"])?;
            }
        }
        if layout == "list" {
            let entries = page["entries"].as_array().map(Vec::as_slice).unwrap_or(&[]);
            if entries.len() > 32 {
                return Err(format!("too many entries on page {id}"));
            }
            let mut entry_ids = HashSet::new();
            for entry in entries {
                let entry_id = valid_id(&entry["id"], "entry id")?;
                if !entry_ids.insert(entry_id) {
                    return Err(format!("duplicate entry id: {entry_id}"));
                }
                valid_label(&entry["label"], "entry label")?;
                valid_action(&entry["action"])?;
            }
        }
    }
    let encoded = serde_json::to_vec(&snapshot(raw, "en")).map_err(|e| e.to_string())?;
    if encoded.len() > crate::transport::protocol::MAX_MESSAGE {
        return Err("snapshot exceeds 3DS frame limit".into());
    }
    Ok(())
}

fn valid_id<'a>(value: &'a Value, name: &str) -> Result<&'a str, String> {
    let text = value
        .as_str()
        .ok_or_else(|| format!("{name} must be text"))?;
    if text.is_empty() || text.len() > 32 {
        return Err(format!("{name} must contain 1–32 bytes"));
    }
    Ok(text)
}

fn valid_label(value: &Value, name: &str) -> Result<(), String> {
    let check = |text: &str| {
        if text.is_empty() || text.chars().count() > 24 {
            Err(format!("{name} must contain 1–24 characters"))
        } else {
            Ok(())
        }
    };
    if let Some(text) = value.as_str() {
        return check(text);
    }
    let translations = value
        .as_object()
        .ok_or_else(|| format!("{name} must be text or translations"))?;
    if translations.is_empty() {
        return Err(format!("{name} is empty"));
    }
    for text in translations.values() {
        check(
            text.as_str()
                .ok_or_else(|| format!("{name} translation must be text"))?,
        )?;
    }
    Ok(())
}

fn valid_action(value: &Value) -> Result<(), String> {
    let kind = value
        .as_str()
        .or_else(|| value.get("type").and_then(Value::as_str));
    if kind.is_some_and(|kind| !kind.is_empty() && kind.len() <= 64) {
        #[cfg(target_os = "macos")]
        if kind == Some("hotkey") {
            let keys = value["keys"].as_str().ok_or("Hotkey missing keys")?;
            crate::platform::macos::keyboard::validate(keys)?;
        }
        Ok(())
    } else {
        Err("action must have a type of 1–64 bytes".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn current_python_document_produces_safe_snapshot() {
        let source: Value = serde_json::from_str(DEFAULT_CONFIG).unwrap();
        validate(&source).unwrap();
        let snapshot = snapshot(&source, "fr");
        assert_eq!(snapshot["pages"][0]["title"], "Principal");
        assert!(snapshot["pages"][0]["buttons"][0].get("action").is_none());
        assert_eq!(snapshot["pages"][2]["entries"], json!([]));
    }

    #[test]
    fn rejects_duplicate_slots() {
        let mut source: Value = serde_json::from_str(DEFAULT_CONFIG).unwrap();
        source["pages"][0]["buttons"][1]["slot"] = json!(0);
        assert!(validate(&source).unwrap_err().contains("duplicate slot"));
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn rejects_unsupported_hotkey_before_saving() {
        let mut source: Value = serde_json::from_str(DEFAULT_CONFIG).unwrap();
        source["pages"][0]["buttons"][0]["action"] =
            json!({ "type": "hotkey", "keys": "cmd+banana" });
        assert!(validate(&source).is_err());
    }

    #[test]
    fn saves_atomically_and_rejects_stale_revision() {
        let path =
            std::env::temp_dir().join(format!("3decks-config-test-{}.json", std::process::id()));
        let _ = std::fs::remove_file(&path);
        let store = ConfigStore::new(path.clone()).unwrap();
        let mut edited = store.document();
        edited["pages"][0]["title"]["fr"] = json!("Test Rust");
        let saved = store.save(edited.clone()).unwrap();
        assert_eq!(saved["revision"], json!(31));
        assert_eq!(store.snapshot("fr")["pages"][0]["title"], "Test Rust");
        assert!(store.save(edited).unwrap_err().contains("reload"));
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                std::fs::metadata(&path).unwrap().permissions().mode() & 0o777,
                0o600
            );
        }
        let reloaded = ConfigStore::new(path.clone()).unwrap();
        assert_eq!(reloaded.document()["pages"][0]["title"]["fr"], "Test Rust");
        std::fs::remove_file(path).unwrap();
    }
}

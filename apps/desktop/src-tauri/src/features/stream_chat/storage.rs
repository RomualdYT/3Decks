use super::model::Settings;
use serde::{Deserialize, Serialize};
use std::{fs, io::Write, path::Path};

// Never serialize these into editor configuration, snapshots or console frames.
#[derive(Clone, Deserialize, Serialize)]
pub struct Credentials {
    pub client_id: String,
    #[serde(default)]
    pub login: String,
    pub access_token: String,
    pub refresh_token: String,
}

pub fn load_settings(path: &Path) -> Result<Settings, String> {
    match fs::read(path) {
        Ok(bytes) => serde_json::from_slice::<Settings>(&bytes)
            .map_err(|_| "invalid_chat_settings".to_owned())?
            .normalize(),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(Settings::default()),
        Err(_) => Err("chat_settings_unavailable".into()),
    }
}

pub fn save_settings(path: &Path, settings: &Settings) -> Result<(), String> {
    let bytes = serde_json::to_vec_pretty(settings).map_err(|_| "invalid_chat_settings")?;
    let temporary = path.with_extension(format!("{}.tmp", rand::random::<u64>()));
    let result = (|| {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        drop(file);
        fs::rename(&temporary, path)
    })();
    if result.is_err() {
        let _ = fs::remove_file(temporary);
    }
    result.map_err(|_| "chat_settings_unavailable".into())
}

fn entry() -> Result<keyring::Entry, String> {
    keyring::Entry::new("3Decks.Twitch", "stream-chat")
        .map_err(|_| "credential_store_unavailable".into())
}

pub fn load_credentials() -> Result<Option<Credentials>, String> {
    match entry()?.get_password() {
        Ok(value) => serde_json::from_str(&value)
            .map(Some)
            .map_err(|_| "credential_store_unavailable".into()),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(_) => Err("credential_store_unavailable".into()),
    }
}

pub fn save_credentials(credentials: &Credentials) -> Result<(), String> {
    let value = serde_json::to_string(credentials).map_err(|_| "credential_store_unavailable")?;
    entry()?
        .set_password(&value)
        .map_err(|_| "credential_store_unavailable".into())
}

pub fn delete_credentials() -> Result<(), String> {
    match entry()?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(_) => Err("credential_store_unavailable".into()),
    }
}

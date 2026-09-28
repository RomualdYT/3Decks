//! Small persistent diagnostic journal for the native menu.
use std::{fs, io::Write, path::PathBuf, sync::OnceLock};
use tauri::{AppHandle, Manager};

static LOG_PATH: OnceLock<PathBuf> = OnceLock::new();

pub fn init(app: &AppHandle) -> Result<(), String> {
    let directory = app
        .path()
        .app_log_dir()
        .map_err(|error| error.to_string())?;
    fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
    let path = directory.join("3decks.log");
    LOG_PATH
        .set(path)
        .map_err(|_| "Journal already initialized")?;
    append("3Decks started");
    Ok(())
}

pub fn path() -> Option<&'static PathBuf> {
    LOG_PATH.get()
}

pub fn append(message: &str) {
    let Some(path) = LOG_PATH.get() else { return };
    let Ok(mut file) = fs::OpenOptions::new().create(true).append(true).open(path) else {
        return;
    };
    let time = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|value| value.as_secs())
        .unwrap_or(0);
    let safe = message.replace(['\r', '\n'], " ");
    let _ = writeln!(file, "{time} {safe}");
}

//! Notification state shared by the 3DS transport and platform readers.
//! A provider failure must never stop the TCP server.

#[cfg(target_os = "macos")]
#[path = "notifications/macos_reader.rs"]
mod macos_reader;
#[cfg(target_os = "windows")]
#[path = "notifications/windows_history.rs"]
mod windows_history;

use serde_json::{json, Value};
#[cfg(target_os = "macos")]
use std::path::PathBuf;

const MAX_NOTIFICATIONS: usize = 8;
const MAX_PAYLOAD_NOTIFICATIONS: usize = 4;

pub struct NotificationUpdate {
    pub notifications: Vec<Value>,
    pub newest: Option<Value>,
    pub count: usize,
}

pub struct NotificationReader {
    #[cfg(target_os = "macos")]
    path: PathBuf,
    #[cfg(target_os = "macos")]
    last_key: Option<String>,
    #[cfg(target_os = "windows")]
    history: windows_history::History,
    status: Value,
}

impl NotificationReader {
    pub fn new(data_directory: &std::path::Path) -> Self {
        #[cfg(target_os = "macos")]
        {
            let _ = data_directory;
            let path = std::env::var_os("HOME")
                .map(PathBuf::from)
                .unwrap_or_default()
                .join("Library/Group Containers/group.com.apple.usernoted/db2/db");
            let present = path.is_file();
            Self {
                path,
                last_key: None,
                status: status(false, present, ""),
            }
        }
        #[cfg(not(target_os = "macos"))]
        {
            #[cfg(target_os = "windows")]
            let history_path = data_directory.join("notification-history.sqlite3");
            #[cfg(target_os = "windows")]
            let mut status = crate::platform::windows::notifications::initial_status();
            #[cfg(target_os = "windows")]
            let history = match windows_history::History::open(history_path.clone()) {
                Ok(history) => history,
                Err(error) => {
                    status["error"] =
                        json!(format!("Notification history could not be loaded: {error}"));
                    windows_history::History::empty(history_path)
                }
            };
            #[cfg(not(target_os = "windows"))]
            let _ = data_directory;
            #[cfg(not(target_os = "windows"))]
            let status = status(
                false,
                false,
                "Notification provider is not implemented on this platform",
            );
            Self {
                #[cfg(target_os = "windows")]
                history,
                status,
            }
        }
    }

    pub fn status(&self) -> Value {
        self.status.clone()
    }

    #[cfg(target_os = "windows")]
    pub fn set_status(&mut self, status: Value) {
        self.status = status;
    }

    pub fn available(&self) -> bool {
        self.status["available"].as_bool() == Some(true)
    }

    pub fn read(&mut self, enabled: bool) -> NotificationUpdate {
        let empty = || NotificationUpdate {
            notifications: Vec::new(),
            newest: None,
            count: 0,
        };
        if !enabled {
            #[cfg(target_os = "macos")]
            {
                self.last_key = None;
            }
            #[cfg(target_os = "macos")]
            let present = self.path.is_file();
            #[cfg(all(not(target_os = "macos"), not(target_os = "windows")))]
            let present = false;
            #[cfg(target_os = "windows")]
            {
                let clear_error = self.history.clear().err();
                self.status = crate::platform::windows::notifications::status();
                if let Some(error) = clear_error {
                    self.status["error"] = json!(format!(
                        "Notification history could not be cleared: {error}"
                    ));
                }
                return empty();
            }
            #[cfg(not(target_os = "windows"))]
            {
                self.status = status(false, present, "");
            }
            #[cfg(not(target_os = "windows"))]
            return empty();
        }
        #[cfg(target_os = "macos")]
        {
            if !self.path.is_file() {
                self.status = status(true, false, "Centre de notifications introuvable");
                return empty();
            }
            match macos_reader::read(&self.path) {
                Ok(items) => {
                    self.status = status(true, true, "");
                    let newest = items.first().and_then(|(key, payload)| {
                        let previous = self.last_key.replace(key.clone());
                        previous.filter(|old| old != key).map(|_| payload.clone())
                    });
                    NotificationUpdate {
                        count: items.len(),
                        notifications: items
                            .into_iter()
                            .take(MAX_PAYLOAD_NOTIFICATIONS)
                            .map(|(_, payload)| payload)
                            .collect(),
                        newest,
                    }
                }
                Err(error) => {
                    self.status = status(true, false, &error);
                    empty()
                }
            }
        }
        #[cfg(not(target_os = "macos"))]
        {
            #[cfg(target_os = "windows")]
            {
                match crate::platform::windows::notifications::read() {
                    Ok(update) => {
                        self.status = update.status;
                        if self.status["access"].as_str() != Some("Allowed") {
                            if let Err(error) = self.history.clear() {
                                self.status["error"] = json!(format!(
                                    "Notification history could not be cleared: {error}"
                                ));
                            }
                            return empty();
                        }
                        let (result, history_error) = self.history.ingest(update.items);
                        if let Some(error) = history_error {
                            self.status["error"] =
                                json!(format!("Notification history could not be saved: {error}"));
                        }
                        result
                    }
                    Err(error) => {
                        self.status = crate::platform::windows::notifications::error_status(&error);
                        empty()
                    }
                }
            }
            #[cfg(not(target_os = "windows"))]
            {
                self.status = status(
                    true,
                    false,
                    "Notification provider is not implemented on this platform",
                );
                empty()
            }
        }
    }
}

fn status(enabled: bool, available: bool, error: &str) -> Value {
    json!({
        "provider": if cfg!(target_os = "macos") { "macos_notification_database" } else if cfg!(target_os = "windows") { "windows_user_notification_listener" } else { "none" },
        "enabled": enabled,
        "available": available,
        "access": if !enabled { "Disabled" } else if available { "Allowed" } else { "Unavailable" },
        "error": error,
        "settings_action": if enabled && !available && cfg!(target_os = "macos") { "notifications" } else if enabled && !available && cfg!(target_os = "windows") { "notifications" } else { "" },
    })
}

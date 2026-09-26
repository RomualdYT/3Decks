//! Windows notification listener, gated by package identity and user consent.
//!
//! The API is intentionally read-only here. Windows exposes the currently
//! retained notification-center items, not a durable history of dismissed
//! notifications; the app mirrors this bounded current list to the 3DS.

use serde_json::{json, Value};
use std::collections::HashSet;
use std::time::{SystemTime, UNIX_EPOCH};
use windows::Win32::Foundation::ERROR_INSUFFICIENT_BUFFER;
use windows::Win32::Storage::Packaging::Appx::GetCurrentPackageFullName;
use windows::Win32::System::WinRT::{RoInitialize, RoUninitialize, RO_INIT_MULTITHREADED};
use windows::UI::Notifications::Management::{
    UserNotificationListener, UserNotificationListenerAccessStatus,
};
use windows::UI::Notifications::{NotificationKinds, UserNotification};

const MAX_AGE_SECONDS: u64 = 6 * 60 * 60;
const WINDOWS_EPOCH_OFFSET_TICKS: i64 = 116_444_736_000_000_000;
const TICKS_PER_SECOND: i64 = 10_000_000;

struct WinRtApartment;

impl WinRtApartment {
    fn enter() -> Result<Self, String> {
        unsafe { RoInitialize(RO_INIT_MULTITHREADED) }.map_err(|error| error.to_string())?;
        Ok(Self)
    }
}

impl Drop for WinRtApartment {
    fn drop(&mut self) {
        unsafe { RoUninitialize() };
    }
}

#[derive(Debug)]
struct Access {
    value: &'static str,
    available: bool,
    error: String,
}

pub struct NotificationItem {
    pub key: String,
    pub payload: Value,
    pub created_unix: u64,
}

pub struct NotificationRead {
    pub status: Value,
    pub items: Vec<NotificationItem>,
}

fn has_package_identity() -> bool {
    let mut length = 0;
    let result = unsafe { GetCurrentPackageFullName(&mut length, None) };
    result == ERROR_INSUFFICIENT_BUFFER
}

fn access_status() -> Access {
    if !has_package_identity() {
        return Access {
            value: "Unavailable",
            available: false,
            error: "Windows notification access requires a packaged app identity (MSIX).".into(),
        };
    }
    let Ok(_apartment) = WinRtApartment::enter() else {
        return Access {
            value: "Unavailable",
            available: false,
            error: "Windows Runtime could not be initialized for notification access.".into(),
        };
    };
    match UserNotificationListener::Current().and_then(|listener| listener.GetAccessStatus()) {
        Ok(status) if status == UserNotificationListenerAccessStatus::Allowed => Access {
            value: "Allowed",
            available: true,
            error: String::new(),
        },
        Ok(status) if status == UserNotificationListenerAccessStatus::Denied => Access {
            value: "Denied",
            available: false,
            error: "Notification access was denied. Allow 3Decks in Windows notification settings."
                .into(),
        },
        Ok(_) => Access {
            value: "Unspecified",
            available: false,
            error: String::new(),
        },
        Err(error) => Access {
            value: "Unavailable",
            available: false,
            error: format!("The notification listener is unavailable: {error}"),
        },
    }
}

pub fn status() -> Value {
    let access = access_status();
    status_value(false, access)
}

pub fn initial_status() -> Value {
    if !has_package_identity() {
        return status_value(
            false,
            Access {
                value: "Unavailable",
                available: false,
                error: "Windows notification access requires a packaged app identity (MSIX)."
                    .into(),
            },
        );
    }
    status_value(
        false,
        Access {
            value: "Unspecified",
            available: false,
            error: String::new(),
        },
    )
}

fn status_value(enabled: bool, access: Access) -> Value {
    json!({
        "provider":"windows_user_notification_listener",
        "enabled":enabled,
        "available":access.available,
        "access":access.value,
        "error":access.error,
        "settings_action":if access.value == "Denied" { "notifications" } else { "" },
    })
}

pub fn error_status(error: &str) -> Value {
    status_value(
        true,
        Access {
            value: "Unavailable",
            available: false,
            error: error.to_owned(),
        },
    )
}

pub fn read() -> Result<NotificationRead, String> {
    let _apartment = WinRtApartment::enter()?;
    let listener = UserNotificationListener::Current()
        .map_err(|error| format!("Windows notification listener is unavailable: {error}"))?;
    let access = listener
        .GetAccessStatus()
        .map_err(|error| error.to_string())?;
    let access_value = if access == UserNotificationListenerAccessStatus::Allowed {
        "Allowed"
    } else if access == UserNotificationListenerAccessStatus::Denied {
        "Denied"
    } else {
        "Unspecified"
    };
    let mut status = status_value(
        true,
        Access {
            value: access_value,
            available: access_value == "Allowed",
            error: String::new(),
        },
    );
    if access != UserNotificationListenerAccessStatus::Allowed {
        if access_value == "Denied" {
            status["error"] = json!(
                "Notification access was denied. Allow 3Decks in Windows notification settings."
            );
        }
        return Ok(NotificationRead {
            status,
            items: Vec::new(),
        });
    }

    let notifications = listener
        .GetNotificationsAsync(NotificationKinds::Toast)
        .map_err(|error| error.to_string())?
        .join()
        .map_err(|error| error.to_string())?;
    let count = notifications.Size().map_err(|error| error.to_string())?;
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let mut items = Vec::new();
    for index in 0..count {
        let Ok(notification) = notifications.GetAt(index) else {
            continue;
        };
        if let Some(item) = decode(&notification, now) {
            items.push(item);
        }
    }
    items.sort_by(|left, right| right.created_unix.cmp(&left.created_unix));
    let mut seen = HashSet::new();
    items.retain(|item| seen.insert(item.key.clone()));
    items.truncate(8);
    Ok(NotificationRead { status, items })
}

fn decode(notification: &UserNotification, now: u64) -> Option<NotificationItem> {
    let id = notification.Id().ok()?;
    let created = notification.CreationTime().ok()?.UniversalTime;
    let unix_ticks = created.checked_sub(WINDOWS_EPOCH_OFFSET_TICKS)?;
    if unix_ticks < 0 {
        return None;
    }
    let created_unix = (unix_ticks / TICKS_PER_SECOND) as u64;
    let age = now.saturating_sub(created_unix);
    if age > MAX_AGE_SECONDS {
        return None;
    }
    let app = notification
        .AppInfo()
        .ok()
        .and_then(|info| info.DisplayInfo().ok())
        .and_then(|info| info.DisplayName().ok())
        .map(|name| name.to_string())
        .filter(|name| !name.trim().is_empty())
        .map(|name| name.chars().take(128).collect::<String>())
        .unwrap_or_else(|| "Windows app".into());
    let text = notification
        .Notification()
        .ok()?
        .Visual()
        .ok()?
        .GetBinding(&"ToastGeneric".into())
        .ok()?
        .GetTextElements()
        .ok()?;
    let mut lines = Vec::new();
    for index in 0..text.Size().ok()?.min(8) {
        if let Ok(element) = text.GetAt(index) {
            if let Ok(value) = element.Text() {
                let value = value.to_string();
                let value = value.trim();
                if !value.is_empty() {
                    lines.push(value.chars().take(512).collect::<String>());
                }
            }
        }
    }
    let title = lines.first()?.chars().take(256).collect::<String>();
    let body = lines
        .iter()
        .skip(1)
        .cloned()
        .collect::<Vec<_>>()
        .join(" — ")
        .chars()
        .take(1024)
        .collect::<String>();
    let key = format!("{created_unix}:{id}:{app}:{title}");
    let mut payload = json!({
        "app":app,
        "title":title,
        "icon":notification_icon(&app),
        "age":age,
    });
    if !body.is_empty() {
        payload["body"] = json!(body);
    }
    Some(NotificationItem {
        key,
        payload,
        created_unix,
    })
}

fn notification_icon(app: &str) -> &'static str {
    let name = app.to_ascii_lowercase();
    if name.contains("mail") || name.contains("outlook") {
        "page"
    } else if name.contains("music") || name.contains("spotify") {
        "music"
    } else if name.contains("browser") || name.contains("edge") || name.contains("chrome") {
        "browser"
    } else if name.contains("chat") || name.contains("discord") || name.contains("slack") {
        "chat"
    } else {
        "star"
    }
}

pub async fn request_access_on_ui(app: &tauri::AppHandle) -> Result<String, String> {
    if !has_package_identity() {
        return Err("Windows notification access requires a packaged app identity (MSIX).".into());
    }
    let (sender, receiver) = tokio::sync::oneshot::channel();
    app.run_on_main_thread(move || {
        let operation = UserNotificationListener::Current()
            .and_then(|listener| listener.RequestAccessAsync())
            .map_err(|error| error.to_string());
        let _ = sender.send(operation);
    })
    .map_err(|error| error.to_string())?;
    let operation = receiver.await.map_err(|error| error.to_string())??;
    let access =
        tokio::task::spawn_blocking(move || operation.join().map_err(|error| error.to_string()))
            .await
            .map_err(|error| error.to_string())??;
    Ok(if access == UserNotificationListenerAccessStatus::Allowed {
        "Allowed"
    } else if access == UserNotificationListenerAccessStatus::Denied {
        "Denied"
    } else {
        "Unspecified"
    }
    .into())
}

//! Read the macOS notification database without modifying it. This is an
//! undocumented system format, so an unreadable database only disables this
//! feature; it must never stop the TCP server.

use serde_json::{json, Value};
#[cfg(target_os = "macos")]
use std::{
    collections::HashSet,
    io::Cursor,
    path::PathBuf,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

const MAX_NOTIFICATIONS: usize = 8;
const MAX_PAYLOAD_NOTIFICATIONS: usize = 4;
#[cfg(target_os = "macos")]
const APPLE_EPOCH: f64 = 978_307_200.0;
#[cfg(target_os = "macos")]
const MAX_AGE: f64 = 6.0 * 60.0 * 60.0;

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
    status: Value,
}

impl NotificationReader {
    pub fn new() -> Self {
        #[cfg(target_os = "macos")]
        {
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
            Self {
                status: status(
                    false,
                    false,
                    "Notification provider is not implemented on this platform",
                ),
            }
        }
    }

    pub fn status(&self) -> Value {
        self.status.clone()
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
            #[cfg(not(target_os = "macos"))]
            let present = false;
            self.status = status(false, present, "");
            return empty();
        }
        #[cfg(target_os = "macos")]
        {
            if !self.path.is_file() {
                self.status = status(true, false, "Centre de notifications introuvable");
                return empty();
            }
            match self.read_macos() {
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
            self.status = status(
                true,
                false,
                "Notification provider is not implemented on this platform",
            );
            empty()
        }
    }

    #[cfg(target_os = "macos")]
    fn read_macos(&self) -> Result<Vec<(String, Value)>, String> {
        use rusqlite::{Connection, OpenFlags};
        let connection = Connection::open_with_flags(
            &self.path,
            OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
        )
        .map_err(|error| error.to_string())?;
        connection
            .busy_timeout(Duration::from_millis(500))
            .map_err(|error| error.to_string())?;
        let mut query = connection
            .prepare(
                "SELECT rec.delivered_date, app.identifier, rec.data \
             FROM record rec JOIN app ON rec.app_id = app.app_id \
             WHERE rec.delivered_date IS NOT NULL \
             ORDER BY rec.delivered_date DESC LIMIT 40",
            )
            .map_err(|error| error.to_string())?;
        let rows = query
            .query_map([], |row| {
                Ok((
                    row.get::<_, f64>(0)?,
                    row.get::<_, Option<String>>(1)?.unwrap_or_default(),
                    row.get::<_, Option<Vec<u8>>>(2)?.unwrap_or_default(),
                ))
            })
            .map_err(|error| error.to_string())?;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        let mut seen = HashSet::new();
        let mut result = Vec::new();
        for row in rows {
            let (delivered, bundle, data) = row.map_err(|error| error.to_string())?;
            if let Some((key, payload)) = decode(delivered, &bundle, &data, now) {
                if seen.insert(key.clone()) {
                    result.push((key, payload));
                    if result.len() == MAX_NOTIFICATIONS {
                        break;
                    }
                }
            }
        }
        Ok(result)
    }
}

fn status(enabled: bool, available: bool, error: &str) -> Value {
    json!({
        "provider": if cfg!(target_os = "macos") { "macos_notification_database" } else { "none" },
        "enabled": enabled,
        "available": available,
        "access": if !enabled { "Disabled" } else if available { "Allowed" } else { "Unavailable" },
        "error": error,
        "settings_action": if enabled && !available && cfg!(target_os = "macos") { "notifications" } else { "" },
    })
}

#[cfg(target_os = "macos")]
fn decode(delivered: f64, bundle: &str, data: &[u8], now: f64) -> Option<(String, Value)> {
    let age = now - (delivered + APPLE_EPOCH);
    if !age.is_finite() || !(-60.0..=MAX_AGE).contains(&age) {
        return None;
    }
    let plist = plist::Value::from_reader(Cursor::new(data)).ok()?;
    let request = plist.as_dictionary()?.get("req")?.as_dictionary()?;
    let field = |name: &str| {
        request
            .get(name)
            .and_then(plist::Value::as_string)
            .unwrap_or("")
            .trim()
    };
    let title = field("titl");
    let subtitle = field("subt");
    let body = field("body");
    if title.is_empty() && body.is_empty() {
        return None;
    }
    let app = app_name(bundle);
    let body = if !subtitle.is_empty() && subtitle != title {
        if body.is_empty() {
            subtitle.to_owned()
        } else {
            format!("{subtitle} — {body}")
        }
    } else {
        body.to_owned()
    };
    let key = format!("{bundle}|{title}|{body}");
    let mut payload = json!({
        "app": app, "title": if title.is_empty() { app.as_str() } else { title },
        "icon": icon(&app), "age": age.max(0.0) as u64,
    });
    if !body.is_empty() {
        payload["body"] = json!(body);
    }
    Some((key, payload))
}

#[cfg(target_os = "macos")]
fn app_name(bundle: &str) -> String {
    let bundle = bundle.rsplit(':').next().unwrap_or(bundle);
    let known = match bundle {
        "com.apple.mobilesms" => "Messages",
        "com.apple.mail" => "Mail",
        "com.apple.facetime" => "FaceTime",
        "com.apple.reminders" => "Rappels",
        "com.apple.iCal" => "Calendrier",
        "com.apple.music" => "Musique",
        "com.spotify.client" => "Spotify",
        "com.tinyspeck.slackmacgap" => "Slack",
        "com.hnc.Discord" => "Discord",
        "com.apple.finder" => "Finder",
        "com.apple.Safari" => "Safari",
        "com.google.Chrome" => "Chrome",
        "com.openai.chat" => "ChatGPT",
        "com.openai.codex" => "Codex",
        "com.microsoft.VSCode" => "VS Code",
        "com.docker.docker" => "Docker",
        _ => "",
    };
    if !known.is_empty() {
        return known.to_owned();
    }
    let tail = bundle.rsplit('.').next().unwrap_or(bundle);
    let mut chars = tail.chars();
    match chars.next() {
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
        None => String::new(),
    }
}

#[cfg(target_os = "macos")]
fn icon(app: &str) -> &'static str {
    match app {
        "Messages" | "Slack" | "Discord" => "chat",
        "Mail" | "Calendrier" => "page",
        "FaceTime" => "video",
        "Spotify" | "Musique" | "Podcasts" => "music",
        "Safari" | "Chrome" | "Firefox" | "Edge" => "browser",
        "Codex" | "Terminal" => "terminal",
        "Finder" => "folder",
        "Rappels" => "star",
        "ChatGPT" | "VS Code" | "Docker" => "app",
        _ => "star",
    }
}

#[cfg(all(test, target_os = "macos"))]
mod tests {
    use super::*;

    fn sample_plist(title: &str) -> Vec<u8> {
        let mut request = plist::Dictionary::new();
        request.insert("titl".into(), plist::Value::String(title.into()));
        request.insert("subt".into(), plist::Value::String("Alice".into()));
        request.insert("body".into(), plist::Value::String("Message".into()));
        let mut root = plist::Dictionary::new();
        root.insert("req".into(), plist::Value::Dictionary(request));
        let mut bytes = Vec::new();
        plist::to_writer_binary(&mut bytes, &root).unwrap();
        bytes
    }

    #[test]
    fn decodes_only_recent_notifications() {
        let bytes = sample_plist("Bonjour");
        let now = APPLE_EPOCH + 100_000.0;
        let (_, payload) = decode(100_000.0, "com.apple.mobilesms", &bytes, now).unwrap();
        assert_eq!(payload["app"], "Messages");
        assert_eq!(payload["body"], "Alice — Message");
        assert!(decode(100_000.0, "com.apple.mail", &bytes, now + MAX_AGE + 1.0).is_none());
        assert!(decode(100_000.0, "com.apple.mail", b"invalid", now).is_none());
    }

    #[test]
    fn reads_database_without_reannouncing_history() {
        let path = std::env::temp_dir().join(format!(
            "3decks-notifications-{}-{}.db",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let connection = rusqlite::Connection::open(&path).unwrap();
        connection.execute_batch("CREATE TABLE app(app_id INTEGER PRIMARY KEY, identifier TEXT); CREATE TABLE record(app_id INTEGER, delivered_date REAL, data BLOB); INSERT INTO app VALUES (1, 'com.apple.mobilesms');").unwrap();
        let delivered = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64()
            - APPLE_EPOCH;
        connection
            .execute(
                "INSERT INTO record VALUES (1, ?1, ?2)",
                rusqlite::params![delivered, sample_plist("Old")],
            )
            .unwrap();
        let mut reader = NotificationReader {
            path: path.clone(),
            last_key: None,
            status: status(false, true, ""),
        };
        let first = reader.read(true);
        assert_eq!(first.count, 1);
        assert!(first.newest.is_none());
        assert!(reader.available());
        connection
            .execute(
                "INSERT INTO record VALUES (1, ?1, ?2)",
                rusqlite::params![delivered + 1.0, sample_plist("New")],
            )
            .unwrap();
        let second = reader.read(true);
        assert_eq!(second.count, 2);
        assert_eq!(second.newest.unwrap()["title"], "New");
        assert!(reader.read(true).newest.is_none());
        drop(connection);
        std::fs::remove_file(path).unwrap();
    }
}

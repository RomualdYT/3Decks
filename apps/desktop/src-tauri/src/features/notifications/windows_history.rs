//! Bounded local history for notifications observed through WinRT.
//! Windows only exposes notifications still held in its notification center.

use super::{MAX_NOTIFICATIONS, MAX_PAYLOAD_NOTIFICATIONS, NotificationUpdate};
use crate::platform::windows::notifications::NotificationItem;
use rusqlite::{Connection, params};
use serde_json::{Value, json};
use std::{
    path::PathBuf,
    time::{SystemTime, UNIX_EPOCH},
};

const RETENTION_SECONDS: u64 = 6 * 60 * 60;

struct Entry {
    key: String,
    created: u64,
    payload: Value,
}

pub(super) struct History {
    path: PathBuf,
    entries: Vec<Entry>,
    primed: bool,
    cleared: bool,
}

impl History {
    pub(super) fn open(path: PathBuf) -> Result<Self, String> {
        let connection = connection(&path)?;
        let now = unix_now();
        prune_database(&connection, now)?;
        let mut statement = connection
            .prepare("SELECT key, created_unix, payload FROM notification_history ORDER BY created_unix DESC, key DESC LIMIT ?1")
            .map_err(|error| error.to_string())?;
        let rows = statement
            .query_map(params![MAX_NOTIFICATIONS as i64], |row| {
                let created = row.get::<_, i64>(1)?;
                Ok((
                    row.get::<_, String>(0)?,
                    u64::try_from(created)
                        .map_err(|_| rusqlite::Error::IntegralValueOutOfRange(1, created))?,
                    row.get::<_, String>(2)?,
                ))
            })
            .map_err(|error| error.to_string())?;
        let mut entries = Vec::new();
        for row in rows {
            let (key, created, raw) = row.map_err(|error| error.to_string())?;
            if let Ok(payload) = serde_json::from_str(&raw) {
                entries.push(Entry {
                    key,
                    created,
                    payload,
                });
            }
        }
        Ok(Self {
            path,
            entries,
            primed: false,
            cleared: false,
        })
    }

    pub(super) fn empty(path: PathBuf) -> Self {
        Self {
            path,
            entries: Vec::new(),
            primed: false,
            cleared: false,
        }
    }

    pub(super) fn clear(&mut self) -> Result<(), String> {
        if self.cleared {
            return Ok(());
        }
        self.entries.clear();
        self.primed = false;
        let connection = connection(&self.path)?;
        connection
            .execute("DELETE FROM notification_history", [])
            .map_err(|error| error.to_string())?;
        self.cleared = true;
        Ok(())
    }

    pub(super) fn ingest(
        &mut self,
        items: Vec<NotificationItem>,
    ) -> (NotificationUpdate, Option<String>) {
        let now = unix_now();
        let newest = if self.primed {
            items
                .iter()
                .find(|item| !self.entries.iter().any(|entry| entry.key == item.key))
                .map(|item| item.payload.clone())
        } else {
            None
        };
        self.primed = true;

        let mut changed = false;
        for item in items {
            if !self.entries.iter().any(|entry| entry.key == item.key) {
                self.entries.push(Entry {
                    key: item.key,
                    created: item.created_unix,
                    payload: item.payload,
                });
                changed = true;
                self.cleared = false;
            }
        }
        let original_len = self.entries.len();
        self.entries
            .retain(|entry| now.saturating_sub(entry.created) <= RETENTION_SECONDS);
        self.entries.sort_by(|left, right| {
            right
                .created
                .cmp(&left.created)
                .then_with(|| right.key.cmp(&left.key))
        });
        self.entries.truncate(MAX_NOTIFICATIONS);
        changed |= self.entries.len() != original_len;

        let error = changed.then(|| self.persist(now).err()).flatten();
        let notifications = self
            .entries
            .iter()
            .take(MAX_PAYLOAD_NOTIFICATIONS)
            .map(|entry| {
                let mut payload = entry.payload.clone();
                payload["age"] = json!(now.saturating_sub(entry.created));
                payload
            })
            .collect();
        (
            NotificationUpdate {
                count: self.entries.len(),
                notifications,
                newest,
            },
            error,
        )
    }

    fn persist(&self, now: u64) -> Result<(), String> {
        let mut connection = connection(&self.path)?;
        let transaction = connection
            .transaction()
            .map_err(|error| error.to_string())?;
        for entry in &self.entries {
            transaction.execute(
                "INSERT OR IGNORE INTO notification_history (key, created_unix, payload) VALUES (?1, ?2, ?3)",
                params![entry.key, sqlite_timestamp(entry.created)?, entry.payload.to_string()],
            ).map_err(|error| error.to_string())?;
        }
        prune_database(&transaction, now)?;
        transaction.commit().map_err(|error| error.to_string())
    }
}

fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

// SQLite INTEGER values are signed, while notification timestamps are unsigned.
fn sqlite_timestamp(timestamp: u64) -> Result<i64, String> {
    i64::try_from(timestamp)
        .map_err(|_| "Notification timestamp exceeds SQLite's integer range".into())
}

fn connection(path: &PathBuf) -> Result<Connection, String> {
    let connection = Connection::open(path).map_err(|error| error.to_string())?;
    connection
        .execute_batch(
            "CREATE TABLE IF NOT EXISTS notification_history (
        key TEXT PRIMARY KEY NOT NULL,
        created_unix INTEGER NOT NULL,
        payload TEXT NOT NULL
    );",
        )
        .map_err(|error| error.to_string())?;
    Ok(connection)
}

fn prune_database(connection: &Connection, now: u64) -> Result<(), String> {
    connection
        .execute(
            "DELETE FROM notification_history WHERE created_unix < ?1 OR key NOT IN (
            SELECT key FROM notification_history ORDER BY created_unix DESC, key DESC LIMIT ?2
        )",
            params![
                sqlite_timestamp(now.saturating_sub(RETENTION_SECONDS))?,
                MAX_NOTIFICATIONS as i64
            ],
        )
        .map_err(|error| error.to_string())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn orders_batches_and_restores_history_without_reannouncing_it() {
        let path = std::env::temp_dir().join(format!(
            "3decks-history-{}-{}.db",
            std::process::id(),
            unix_now()
        ));
        let now = unix_now();
        let mut history = History::open(path.clone()).unwrap();
        let items = vec![
            NotificationItem {
                key: "newer".into(),
                created_unix: now,
                payload: json!({"title":"Newer"}),
            },
            NotificationItem {
                key: "older".into(),
                created_unix: now - 2,
                payload: json!({"title":"Older"}),
            },
        ];
        let (update, error) = history.ingest(items);
        assert!(error.is_none());
        assert!(update.newest.is_none());
        assert_eq!(update.notifications[0]["title"], "Newer");
        assert_eq!(update.notifications[1]["title"], "Older");
        let mut restored = History::open(path.clone()).unwrap();
        let (update, _) = restored.ingest(vec![NotificationItem {
            key: "newer".into(),
            created_unix: now,
            payload: json!({"title":"Newer"}),
        }]);
        assert!(update.newest.is_none());
        assert_eq!(update.count, 2);
        restored.clear().unwrap();
        assert_eq!(History::open(path.clone()).unwrap().entries.len(), 0);
        let _ = std::fs::remove_file(path);
    }
}

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

pub const HISTORY_LIMIT: usize = 20;

// Public application identifier shared by official 3Decks installations.
const DEFAULT_CLIENT_ID: &str = "zcrmckpe4i1v332agcjptcbwjnrswo";

fn bundled_client_id() -> &'static str {
    option_env!("DECKS_TWITCH_CLIENT_ID")
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .unwrap_or(DEFAULT_CLIENT_ID)
}

#[derive(Clone, Default, Deserialize, Serialize, PartialEq, Eq)]
#[serde(default, deny_unknown_fields)]
pub struct Settings {
    pub enabled: bool,
    pub channel: String,
    pub client_id: String,
    pub timestamps: bool,
    pub hide_commands: bool,
    pub compact: bool,
}

impl Settings {
    pub fn normalize(mut self) -> Result<Self, String> {
        let raw = self.channel.trim();
        self.channel = if raw.contains("://")
            || raw.starts_with("twitch.tv/")
            || raw.starts_with("www.twitch.tv/")
        {
            let candidate = if raw.contains("://") {
                raw.to_owned()
            } else {
                format!("https://{raw}")
            };
            let url = url::Url::parse(&candidate).map_err(|_| "invalid_channel")?;
            if !matches!(url.scheme(), "http" | "https")
                || !matches!(
                    url.host_str(),
                    Some("twitch.tv" | "www.twitch.tv" | "m.twitch.tv")
                )
                || url.port().is_some()
                || !url.username().is_empty()
                || url.password().is_some()
            {
                return Err("invalid_channel".into());
            }
            let name = url.path().trim_matches('/');
            if name.contains('/') {
                return Err("invalid_channel".into());
            }
            name.to_ascii_lowercase()
        } else {
            raw.trim_start_matches('@').to_ascii_lowercase()
        };
        if self.channel.len() > 25
            || !self
                .channel
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || c == b'_')
        {
            return Err("invalid_channel".into());
        }
        self.client_id = self.client_id.trim().to_owned();
        if self.client_id.len() > 128 || !self.client_id.bytes().all(|c| c.is_ascii_alphanumeric())
        {
            return Err("invalid_client_id".into());
        }
        if self.client_id == bundled_client_id() {
            self.client_id.clear();
        }
        Ok(self)
    }

    pub fn client_id(&self) -> String {
        if self.client_id.is_empty() {
            bundled_client_id().to_owned()
        } else {
            self.client_id.clone()
        }
    }
}

#[derive(Clone, Serialize)]
pub struct Message {
    pub id: String,
    pub user_id: String,
    pub author: String,
    pub text: String,
    pub color: String,
    pub time: String,
    pub badges: Vec<super::badges::Badge>,
}

#[derive(Clone, Serialize)]
pub struct Snapshot {
    pub provider: &'static str,
    pub channel: String,
    pub status: String,
    pub timestamps: bool,
    pub compact: bool,
    pub messages: VecDeque<Message>,
    pub badge_revision: u64,
}

impl Default for Snapshot {
    fn default() -> Self {
        Self {
            provider: "twitch",
            channel: String::new(),
            status: "disabled".into(),
            timestamps: false,
            compact: false,
            messages: VecDeque::new(),
            badge_revision: 0,
        }
    }
}

impl Snapshot {
    pub fn push(&mut self, message: Message) {
        if self.messages.iter().any(|item| item.id == message.id) {
            return;
        }
        if self.messages.len() == HISTORY_LIMIT {
            self.messages.pop_front();
        }
        self.messages.push_back(message);
    }
}

/// Bound wire strings by UTF-8 bytes and remove unsupported control characters.
pub fn text(input: &str, max_bytes: usize) -> String {
    let mut result = String::new();
    for c in input.chars() {
        let c = if c.is_whitespace() {
            ' '
        } else if c.is_control() {
            continue;
        } else {
            c
        };
        if result.len() + c.len_utf8() > max_bytes {
            break;
        }
        result.push(c);
    }
    result
}

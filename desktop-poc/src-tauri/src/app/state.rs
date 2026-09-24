use crate::app::config::ConfigStore;
use crate::app::onboarding::OnboardingStore;
use crate::features::artwork::ArtworkCache;
use crate::features::extensions::ExtensionHost;
use crate::features::notifications::NotificationReader;
use crate::features::telemetry::Telemetry;
use crate::platform::windowing::Window;
use rand::{rngs::OsRng, Rng, RngCore};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    collections::HashMap,
    fs,
    io::Write,
    net::IpAddr,
    path::PathBuf,
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc, Mutex, RwLock,
    },
    time::{Duration, Instant},
};
use subtle::ConstantTimeEq;
use tauri::{AppHandle, Emitter, Manager};
use tokio::sync::{broadcast, watch, Semaphore};

fn extension_text(value: &Value, locale: &str, max_bytes: usize) -> String {
    let text = value
        .as_str()
        .or_else(|| value[locale].as_str())
        .or_else(|| value["en"].as_str())
        .unwrap_or("");
    let mut output = String::new();
    for character in text.chars() {
        if output.len() + character.len_utf8() > max_bytes {
            break;
        }
        output.push(character);
    }
    output
}

#[derive(Clone, Serialize)]
pub struct Status {
    pub running: bool,
    pub error: Option<String>,
    pub tcp_port: u16,
    pub discovery_port: u16,
    pub pairing_code: String,
    pub connected: usize,
    pub paired: usize,
    pub config_revision: u64,
    pub volume: Option<u8>,
    pub windows_count: usize,
    pub cpu: Option<u8>,
    pub memory: Option<u8>,
    pub last_event: String,
}

#[derive(Clone, Serialize)]
pub struct ClientSummary {
    pub id: u64,
    pub address: String,
    pub device_id: String,
    pub name: String,
}

#[derive(Default, Serialize, Deserialize)]
struct CredentialFile {
    // Console name -> SHA-256 of the individual bearer token.
    devices: HashMap<String, String>,
}

fn persist_credentials(path: &PathBuf, credentials: &CredentialFile) -> Result<(), String> {
    let bytes = serde_json::to_vec_pretty(credentials).map_err(|error| error.to_string())?;
    let temporary = path.with_extension(format!("{}.tmp", rand::random::<u64>()));
    let mut options = fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options
        .open(&temporary)
        .map_err(|error| error.to_string())?;
    let written = file.write_all(&bytes).and_then(|()| file.sync_all());
    drop(file);
    let result = written.and_then(|()| fs::rename(&temporary, path));
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result.map_err(|error| error.to_string())
}

struct Pairing {
    code: String,
    by_ip: HashMap<IpAddr, Vec<Instant>>,
    all: Vec<Instant>,
}

#[derive(Clone, Copy)]
enum ControlsPause {
    Off,
    Until(Instant),
    Indefinite,
}

impl ControlsPause {
    fn active(self, now: Instant) -> bool {
        match self {
            Self::Off => false,
            Self::Until(until) => now < until,
            Self::Indefinite => true,
        }
    }
}

pub struct Shared {
    app: AppHandle,
    status: Mutex<Status>,
    credentials: Mutex<CredentialFile>,
    pairing: Mutex<Pairing>,
    credentials_path: PathBuf,
    pub config: ConfigStore,
    pub windows: RwLock<Vec<Window>>,
    pub latest_state: RwLock<Value>,
    clients: RwLock<Vec<ClientSummary>>,
    next_client: AtomicU64,
    pub telemetry: Arc<Mutex<Telemetry>>,
    pub notifications: Arc<Mutex<NotificationReader>>,
    pub artwork: Arc<Mutex<ArtworkCache>>,
    pub onboarding: OnboardingStore,
    pub extensions: Arc<tokio::sync::Mutex<ExtensionHost>>,
    pub extension_catalog: RwLock<Value>,
    pub extension_snapshots: RwLock<Value>,
    pub config_updates: watch::Sender<u64>,
    pub state_updates: broadcast::Sender<Value>,
    pub revoked: broadcast::Sender<String>,
    pub actions: Semaphore,
    controls_pause: Mutex<ControlsPause>,
    pub stop: watch::Sender<bool>,
}

fn new_code() -> String {
    format!("{:06}", OsRng.gen_range(0..1_000_000))
}

impl Shared {
    pub fn new(app: AppHandle, tcp_port: u16, discovery_port: u16) -> Result<Self, String> {
        let directory = app.path().app_config_dir().map_err(|e| e.to_string())?;
        fs::create_dir_all(&directory).map_err(|e| e.to_string())?;
        let credentials_path = directory.join("paired-consoles-poc.json");
        let config = ConfigStore::new(directory.join("config.json"))?;
        let config_revision = config.document()["revision"].as_u64().unwrap_or(0);
        let credentials = if credentials_path.exists() {
            serde_json::from_slice(&fs::read(&credentials_path).map_err(|e| e.to_string())?)
                .map_err(|e| format!("Invalid credential store: {e}"))?
        } else {
            CredentialFile::default()
        };
        let code = {
            #[cfg(debug_assertions)]
            {
                std::env::var("DECKS_POC_TEST_PAIR_CODE")
                    .ok()
                    .filter(|value| {
                        value.len() == 6 && value.bytes().all(|byte| byte.is_ascii_digit())
                    })
                    .unwrap_or_else(new_code)
            }
            #[cfg(not(debug_assertions))]
            {
                new_code()
            }
        };
        let paired = credentials.devices.len();
        let (stop, _) = watch::channel(false);
        let (config_updates, _) = watch::channel(config_revision);
        let (state_updates, _) = broadcast::channel(32);
        let (revoked, _) = broadcast::channel(32);
        let extension_host = ExtensionHost::new(directory.join("extensions"))?;
        let extension_catalog = extension_host.catalog();
        Ok(Self {
            app,
            status: Mutex::new(Status {
                running: false,
                error: None,
                tcp_port,
                discovery_port,
                pairing_code: code.clone(),
                connected: 0,
                paired,
                config_revision,
                volume: None,
                windows_count: 0,
                cpu: None,
                memory: None,
                last_event: "Starting server…".into(),
            }),
            credentials: Mutex::new(credentials),
            pairing: Mutex::new(Pairing {
                code,
                by_ip: HashMap::new(),
                all: Vec::new(),
            }),
            credentials_path,
            extensions: Arc::new(tokio::sync::Mutex::new(extension_host)),
            extension_catalog: RwLock::new(extension_catalog),
            extension_snapshots: RwLock::new(serde_json::json!({})),
            config,
            windows: RwLock::new(Vec::new()),
            latest_state: RwLock::new(serde_json::json!({"type":"state.update"})),
            clients: RwLock::new(Vec::new()),
            next_client: AtomicU64::new(1),
            telemetry: Arc::new(Mutex::new(Telemetry::new())),
            notifications: Arc::new(Mutex::new(NotificationReader::new())),
            artwork: Arc::new(Mutex::new(ArtworkCache::default())),
            onboarding: OnboardingStore::new(directory.join("onboarding.json")),
            config_updates,
            state_updates,
            revoked,
            actions: Semaphore::new(1),
            controls_pause: Mutex::new(ControlsPause::Off),
            stop,
        })
    }

    pub fn snapshot(&self) -> Status {
        self.status.lock().unwrap().clone()
    }

    pub fn pause_controls(&self, duration: Option<Duration>) {
        *self.controls_pause.lock().unwrap() = match duration {
            Some(value) => ControlsPause::Until(Instant::now() + value),
            None => ControlsPause::Indefinite,
        };
    }

    pub fn resume_controls(&self) {
        *self.controls_pause.lock().unwrap() = ControlsPause::Off;
    }

    pub fn controls_paused(&self) -> bool {
        let mut pause = self.controls_pause.lock().unwrap();
        if !pause.active(Instant::now()) {
            *pause = ControlsPause::Off;
        }
        pause.active(Instant::now())
    }

    pub fn update(&self, f: impl FnOnce(&mut Status)) {
        let (copy, event) = {
            let mut status = self.status.lock().unwrap();
            let previous = status.last_event.clone();
            f(&mut status);
            let event = (status.last_event != previous).then(|| status.last_event.clone());
            (status.clone(), event)
        };
        if let Some(event) = event {
            crate::app::logging::append(&event);
        }
        let _ = self.app.emit("backend-status", copy);
    }

    pub fn config_snapshot(&self, locale: &str) -> Value {
        let mut snapshot = self.config.snapshot(locale);
        let document = self.config.document();
        let windows = self.windows.read().unwrap();
        if let (Some(pages), Some(configured)) = (
            snapshot["pages"].as_array_mut(),
            document["pages"].as_array(),
        ) {
            for (page, source) in pages.iter_mut().zip(configured) {
                if source["source"].as_str() == Some("windows")
                    && source["layout"].as_str() == Some("list")
                {
                    page["entries"] = Value::Array(
                        windows
                            .iter()
                            .enumerate()
                            .map(|(index, window)| window.entry(index == 0))
                            .collect(),
                    );
                }
                if let Some(reference) = source["source"]
                    .as_str()
                    .and_then(|value| value.strip_prefix("ext:"))
                {
                    if let Some((id, name)) = reference.split_once('/') {
                        let snapshots = self.extension_snapshots.read().unwrap();
                        let entries = snapshots[id]["sources"][name].as_array();
                        let render: Vec<Value> = entries.into_iter().flatten().take(32).enumerate().map(|(index, entry)| {
                            let label = extension_text(&entry["label"], locale, 24);
                            let detail = extension_text(&entry["detail"], locale, 40);
                            let mut rendered = serde_json::json!({"id":entry["id"],"label":label,"icon":entry["icon"],"color":entry["color"],"active":entry["active"]});
                            if source["layout"] == "list" { rendered["detail"] = serde_json::json!(detail); }
                            else { rendered["slot"] = serde_json::json!(index); }
                            rendered
                        }).collect();
                        if source["layout"] == "list" {
                            page["entries"] = serde_json::json!(render);
                        } else {
                            page["buttons"] =
                                serde_json::json!(render.into_iter().take(6).collect::<Vec<_>>());
                        }
                    }
                }
            }
        }
        snapshot
    }

    pub fn dynamic_window(&self, page: &str, id: &str) -> Option<Window> {
        let document = self.config.document();
        let configured = document["pages"]
            .as_array()?
            .iter()
            .find(|item| item["id"].as_str() == Some(page))?;
        if configured["source"].as_str() != Some("windows") {
            return None;
        }
        self.windows
            .read()
            .unwrap()
            .iter()
            .find(|window| window.id() == id)
            .cloned()
    }

    pub fn dynamic_extension_action(&self, page: &str, button: &str) -> Option<Value> {
        let document = self.config.document();
        let configured = document["pages"]
            .as_array()?
            .iter()
            .find(|item| item["id"].as_str() == Some(page))?;
        let reference = configured["source"].as_str()?.strip_prefix("ext:")?;
        let (id, name) = reference.split_once('/')?;
        let snapshots = self.extension_snapshots.read().unwrap();
        let entry = snapshots[id]["sources"][name]
            .as_array()?
            .iter()
            .find(|entry| entry["id"].as_str() == Some(button))?;
        let action = entry["action"]["id"].as_str()?;
        Some(
            serde_json::json!({"type":format!("ext:{id}/{action}"),"arguments":entry["action"]["arguments"]}),
        )
    }

    pub fn clients(&self) -> Vec<ClientSummary> {
        self.clients.read().unwrap().clone()
    }

    pub fn client_connected(&self, name: &str, address: &str) -> u64 {
        let id = self.next_client.fetch_add(1, Ordering::Relaxed);
        let count = {
            let mut clients = self.clients.write().unwrap();
            clients.push(ClientSummary {
                id,
                address: address.into(),
                device_id: name.into(),
                name: name.into(),
            });
            clients.len()
        };
        self.update(|status| {
            status.connected = count;
            status.last_event = format!("Console {name} connected from {address}");
        });
        id
    }

    pub fn client_disconnected(&self, id: u64, name: &str) {
        let count = {
            let mut clients = self.clients.write().unwrap();
            clients.retain(|client| client.id != id);
            clients.len()
        };
        self.update(|status| {
            status.connected = count;
            status.last_event = format!("Console {name} disconnected");
        });
    }

    pub fn paired_devices(&self) -> Vec<Value> {
        self.credentials
            .lock()
            .unwrap()
            .devices
            .keys()
            .map(|name| serde_json::json!({"id":name,"name":name,"created_at":"","last_seen":""}))
            .collect()
    }

    pub fn rotate_pairing(&self) -> String {
        let code = new_code();
        self.pairing.lock().unwrap().code = code.clone();
        self.update(|status| {
            status.pairing_code = code.clone();
            status.last_event = "Pairing code rotated".into();
        });
        code
    }

    pub fn revoke_device(&self, name: &str) -> Result<bool, String> {
        let mut credentials = self.credentials.lock().unwrap();
        if !credentials.devices.contains_key(name) {
            return Ok(false);
        }
        let mut next = CredentialFile {
            devices: credentials.devices.clone(),
        };
        next.devices.remove(name);
        persist_credentials(&self.credentials_path, &next)?;
        *credentials = next;
        let count = credentials.devices.len();
        drop(credentials);
        let _ = self.revoked.send(name.to_owned());
        self.update(|status| {
            status.paired = count;
            status.last_event = format!("Console {name} revoked");
        });
        Ok(true)
    }

    pub fn authenticate(
        &self,
        token: Option<&str>,
        pair_code: Option<&str>,
        device: &str,
        peer: IpAddr,
    ) -> Result<Option<String>, &'static str> {
        if let Some(token) = token {
            let digest = hex::encode(Sha256::digest(token.as_bytes()));
            let credentials = self.credentials.lock().unwrap();
            if credentials
                .devices
                .get(device)
                .is_some_and(|saved| saved.as_bytes().ct_eq(digest.as_bytes()).into())
            {
                return Ok(None);
            }
        }

        let mut pairing = self.pairing.lock().unwrap();
        let now = Instant::now();
        pairing
            .all
            .retain(|at| now.duration_since(*at) < Duration::from_secs(60));
        let attempts = pairing.by_ip.entry(peer).or_default();
        attempts.retain(|at| now.duration_since(*at) < Duration::from_secs(60));
        if attempts.len() >= 5 || pairing.all.len() >= 30 {
            return Err("pairing_rate_limited");
        }
        pairing.by_ip.entry(peer).or_default().push(now);
        pairing.all.push(now);
        if pair_code.map(|code| code.as_bytes().ct_eq(pairing.code.as_bytes()).into()) != Some(true)
        {
            return Err("pairing_required");
        }

        let mut raw = [0_u8; 32];
        OsRng.fill_bytes(&mut raw);
        let issued = hex::encode(raw);
        let digest = hex::encode(Sha256::digest(issued.as_bytes()));
        let mut credentials = self.credentials.lock().unwrap();
        let mut next = CredentialFile {
            devices: credentials.devices.clone(),
        };
        next.devices.insert(device.to_string(), digest);
        persist_credentials(&self.credentials_path, &next).map_err(|_| "credential_store_error")?;
        *credentials = next;
        pairing.code = new_code();
        let new_code = pairing.code.clone();
        let count = credentials.devices.len();
        drop(credentials);
        drop(pairing);
        self.update(|status| {
            status.pairing_code = new_code;
            status.paired = count;
            status.last_event = format!("Console {device} paired");
        });
        Ok(Some(issued))
    }
}

#[cfg(test)]
mod pause_tests {
    use super::ControlsPause;
    use std::time::{Duration, Instant};

    #[test]
    fn timed_pause_expires_but_indefinite_pause_does_not() {
        let now = Instant::now();
        assert!(!ControlsPause::Off.active(now));
        assert!(ControlsPause::Until(now + Duration::from_secs(10)).active(now));
        assert!(!ControlsPause::Until(now - Duration::from_secs(1)).active(now));
        assert!(ControlsPause::Indefinite.active(now));
    }
}

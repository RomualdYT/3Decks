mod badges;
mod model;
mod session;
mod storage;
mod twitch;

pub use model::{Settings, Snapshot};
use serde::Serialize;
use std::{
    path::PathBuf,
    sync::{
        Arc, Mutex, RwLock,
        atomic::{AtomicU64, Ordering},
    },
    time::Duration,
};
use storage::Credentials;
use tokio::{sync::watch, time::Instant};
pub use twitch::Authorization;

#[derive(Serialize)]
pub struct View {
    pub settings: Settings,
    pub snapshot: Snapshot,
    pub account: String,
    pub configured: bool,
    pub supported: bool,
    pub error: Option<String>,
    pub authorization: Option<Authorization>,
}

/// Owns the provider worker and its bounded, secret-free presentation state.
pub struct Service {
    path: PathBuf,
    setup_error: RwLock<Option<String>>,
    settings: Mutex<Settings>,
    credentials: tokio::sync::Mutex<Option<Credentials>>,
    account: RwLock<String>,
    authorization: RwLock<Option<Authorization>>,
    auth_generation: AtomicU64,
    changes: watch::Sender<u64>,
    snapshot: RwLock<Snapshot>,
    http: reqwest::Client,
    badges: Mutex<badges::Cache>,
}

impl Service {
    pub fn new(path: PathBuf) -> Result<Self, String> {
        // Optional integration failures must not prevent the desktop from starting.
        let (settings, mut setup_error) = match storage::load_settings(&path) {
            Ok(settings) => (settings, None),
            Err(error) => (Settings::default(), Some(error)),
        };
        let credentials = if cfg!(any(target_os = "macos", target_os = "windows")) {
            storage::load_credentials()
        } else {
            Ok(None)
        };
        if credentials.is_err() {
            setup_error = Some("credential_store_unavailable".into());
        }
        let status = if credentials.is_err() {
            "credential_store_unavailable"
        } else {
            "disabled"
        };
        let account = credentials
            .as_ref()
            .ok()
            .and_then(|value| value.as_ref())
            .filter(|value| value.client_id == settings.client_id())
            .map(|value| value.login.clone())
            .unwrap_or_default();
        let (changes, _) = watch::channel(0);
        Ok(Self {
            path,
            setup_error: RwLock::new(setup_error),
            settings: Mutex::new(settings),
            credentials: tokio::sync::Mutex::new(credentials.unwrap_or(None)),
            account: RwLock::new(account),
            authorization: RwLock::new(None),
            auth_generation: AtomicU64::new(0),
            changes,
            snapshot: RwLock::new(Snapshot {
                status: status.into(),
                ..Snapshot::default()
            }),
            http: twitch::client(),
            badges: Mutex::new(badges::Cache::default()),
        })
    }

    pub fn snapshot(&self) -> Snapshot {
        let mut snapshot = self.snapshot.read().unwrap().clone();
        snapshot.badge_revision = self.badges.lock().unwrap().revision;
        snapshot
    }

    pub fn view(&self) -> View {
        let settings = self.settings.lock().unwrap().clone();
        View {
            configured: !settings.client_id().is_empty(),
            settings,
            error: self.setup_error.read().unwrap().clone(),
            snapshot: self.snapshot(),
            supported: cfg!(any(target_os = "macos", target_os = "windows")),
            account: self.account.read().unwrap().clone(),
            authorization: self.authorization.read().unwrap().clone(),
        }
    }

    fn notify(&self) {
        self.changes
            .send_modify(|revision| *revision = revision.wrapping_add(1));
    }
    fn set_status(&self, status: &str) {
        self.snapshot.write().unwrap().status = status.into();
    }

    pub fn configure(&self, candidate: Settings) -> Result<View, String> {
        let candidate = candidate.normalize()?;
        let mut settings = self.settings.lock().unwrap();
        storage::save_settings(&self.path, &candidate)?;
        *self.setup_error.write().unwrap() = None;
        let reconnect = settings.enabled != candidate.enabled
            || settings.channel != candidate.channel
            || settings.client_id() != candidate.client_id();
        if settings.channel != candidate.channel
            || settings.client_id() != candidate.client_id()
            || !candidate.enabled
        {
            self.snapshot.write().unwrap().messages.clear();
        }
        if settings.client_id() != candidate.client_id() {
            self.auth_generation.fetch_add(1, Ordering::SeqCst);
            *self.authorization.write().unwrap() = None;
            self.account.write().unwrap().clear();
        }
        {
            let mut snapshot = self.snapshot.write().unwrap();
            snapshot.channel = candidate.channel.clone();
            snapshot.timestamps = candidate.timestamps;
            snapshot.compact = candidate.compact;
        }
        *settings = candidate;
        drop(settings);
        if reconnect {
            self.notify();
        }
        Ok(self.view())
    }

    pub async fn authorize(self: &Arc<Self>) -> Result<View, String> {
        if !cfg!(any(target_os = "macos", target_os = "windows")) {
            return Err("unsupported_platform".into());
        }
        let id = self.settings.lock().unwrap().client_id();
        if id.is_empty() {
            return Err("client_id_required".into());
        }
        let generation = self.auth_generation.fetch_add(1, Ordering::SeqCst) + 1;
        let grant = twitch::device(&self.http, &id).await?;
        if self.auth_generation.load(Ordering::SeqCst) != generation {
            return Err("authorization_cancelled".into());
        }
        *self.authorization.write().unwrap() = Some(Authorization {
            code: grant.user_code.clone(),
            url: grant.verification_uri.clone(),
            expires_in: grant.expires_in,
        });
        self.set_status("awaiting_authorization");
        let service = self.clone();
        tokio::spawn(async move {
            let deadline = Instant::now() + Duration::from_secs(grant.expires_in.min(1800));
            let mut interval = grant.interval.clamp(5, 60);
            let result: Result<(), String> = async {
                loop {
                    tokio::time::sleep(Duration::from_secs(interval)).await;
                    if service.auth_generation.load(Ordering::SeqCst) != generation {
                        return Ok(());
                    }
                    if Instant::now() >= deadline {
                        return Err("authorization_expired".into());
                    }
                    match twitch::poll(&service.http, &id, &grant.device_code).await {
                        Ok(Some(mut credentials)) => {
                            let identity = twitch::validate(&service.http, &credentials).await?;
                            let mut current = service.credentials.lock().await;
                            if service.auth_generation.load(Ordering::SeqCst) != generation {
                                return Ok(());
                            }
                            let mut settings = service.settings.lock().unwrap();
                            if service.auth_generation.load(Ordering::SeqCst) != generation
                                || settings.client_id() != id
                            {
                                return Ok(());
                            }
                            credentials.login = identity.login.clone();
                            storage::save_credentials(&credentials)?;
                            *service.setup_error.write().unwrap() = None;
                            *current = Some(credentials);
                            *service.account.write().unwrap() = identity.login.clone();
                            if settings.channel.is_empty() {
                                let mut candidate = settings.clone();
                                candidate.channel = identity.login;
                                match storage::save_settings(&service.path, &candidate) {
                                    Ok(()) => {
                                        service.snapshot.write().unwrap().channel =
                                            candidate.channel.clone();
                                        *settings = candidate;
                                    }
                                    Err(error) => {
                                        *service.setup_error.write().unwrap() = Some(error)
                                    }
                                }
                            }
                            return Ok(());
                        }
                        Ok(None) => {}
                        Err(error) if error == "slow_down" => interval = (interval + 5).min(60),
                        Err(error) => return Err(error),
                    }
                }
            }
            .await;
            if service.auth_generation.load(Ordering::SeqCst) == generation {
                *service.authorization.write().unwrap() = None;
                if let Err(error) = result {
                    service.set_status(&error);
                } else {
                    service.notify();
                }
            }
        });
        Ok(self.view())
    }

    pub async fn disconnect(&self) -> Result<View, String> {
        self.auth_generation.fetch_add(1, Ordering::SeqCst);
        *self.authorization.write().unwrap() = None;
        let mut credentials = self.credentials.lock().await;
        storage::delete_credentials()?;
        *credentials = None;
        self.account.write().unwrap().clear();
        self.snapshot.write().unwrap().messages.clear();
        self.set_status("authorization_required");
        drop(credentials);
        self.notify();
        Ok(self.view())
    }

    async fn identity(&self, id: &str) -> Result<(Credentials, twitch::Identity), String> {
        // Refresh tokens rotate once. Serialize refresh/save with disconnect and authorization.
        let mut current = self.credentials.lock().await;
        let mut credentials = current
            .clone()
            .filter(|credentials| credentials.client_id == id)
            .ok_or("authorization_required")?;
        let identity = match twitch::validate(&self.http, &credentials).await {
            Err(error) if error == "authorization_required" => {
                credentials = twitch::refresh(&self.http, &credentials).await?;
                storage::save_credentials(&credentials)?;
                *current = Some(credentials.clone());
                twitch::validate(&self.http, &credentials).await?
            }
            result => result?,
        };
        *self.account.write().unwrap() = identity.login.clone();
        Ok((credentials, identity))
    }

    pub fn badge_frame(&self, token: u32) -> Option<Vec<u8>> {
        self.badges.lock().unwrap().frame(token)
    }

    pub async fn run(self: Arc<Self>, stop: watch::Receiver<bool>) {
        let mut badge_stop = stop.clone();
        let provider = self.clone();
        tokio::join!(provider.run_provider(stop), async {
            tokio::select! {
                _ = badges::run(&self) => {},
                _ = badge_stop.changed() => {},
            }
        });
    }

    async fn run_provider(self: Arc<Self>, mut stop: watch::Receiver<bool>) {
        let mut changes = self.changes.subscribe();
        let mut backoff = 2;
        loop {
            changes.borrow_and_update();
            if *stop.borrow() {
                break;
            }
            let settings = self.settings.lock().unwrap().clone();
            {
                let mut snapshot = self.snapshot.write().unwrap();
                snapshot.channel = settings.channel.clone();
                snapshot.timestamps = settings.timestamps;
                snapshot.compact = settings.compact;
            }
            let idle = if !settings.enabled {
                Some("disabled")
            } else if settings.client_id().is_empty() {
                Some("client_id_required")
            } else if settings.channel.is_empty() {
                Some("channel_required")
            } else {
                None
            };
            if let Some(status) = idle {
                if self.authorization.read().unwrap().is_none() {
                    self.set_status(status);
                }
                tokio::select! { _ = changes.changed() => {}, _ = stop.changed() => {} }
                continue;
            }
            self.set_status("connecting");
            let result = match self.identity(&settings.client_id()).await {
                Ok((credentials, identity)) => {
                    if changes.has_changed().unwrap_or(true) || *stop.borrow() {
                        continue;
                    }
                    tokio::select! {
                        result = session::run(&self, &settings, &credentials, &identity) => result,
                        _ = changes.changed() => { backoff = 2; continue; },
                        _ = stop.changed() => break,
                    }
                }
                Err(error) => Err(error),
            };
            if let Err(error) = result {
                if self.authorization.read().unwrap().is_none() {
                    self.set_status(&error);
                }
                if matches!(
                    error.as_str(),
                    "authorization_required" | "channel_not_found" | "credential_store_unavailable"
                ) {
                    tokio::select! { _ = changes.changed() => {}, _ = stop.changed() => {} }
                } else {
                    tokio::select! {
                        _ = tokio::time::sleep(Duration::from_secs(backoff)) => backoff = (backoff * 2).min(60),
                        _ = changes.changed() => backoff = 2,
                        _ = stop.changed() => break,
                    }
                }
            }
        }
        self.auth_generation.fetch_add(1, Ordering::SeqCst);
    }
}

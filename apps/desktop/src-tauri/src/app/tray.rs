//! Native tray menu and the small set of desktop-only actions it exposes.
use super::{desktop, logging, state::Shared};
use std::{
    sync::{Arc, Mutex, OnceLock},
    time::Duration,
};
use tauri::{
    menu::{CheckMenuItem, Menu, MenuItem, PredefinedMenuItem, Submenu},
    tray::{TrayIcon, TrayIconBuilder},
    AppHandle, Manager,
};
use tauri_plugin_autostart::ManagerExt as AutostartManagerExt;
use tauri_plugin_dialog::{DialogExt, MessageDialogKind};

const RELEASES_URL: &str = "https://github.com/RomualdYT/3Decks/releases";
const FEATURES: [&str; 4] = ["notifications", "media", "windows", "system_stats"];

fn french() -> bool {
    static FRENCH: OnceLock<bool> = OnceLock::new();
    *FRENCH.get_or_init(|| {
        #[cfg(target_os = "macos")]
        {
            use objc2_foundation::NSLocale;
            NSLocale::preferredLanguages()
                .iter()
                .next()
                .is_some_and(|language| language.to_string().starts_with("fr"))
        }
        #[cfg(not(target_os = "macos"))]
        {
            std::env::var("LANG").unwrap_or_default().starts_with("fr")
        }
    })
}

fn label(fr: &'static str, en: &'static str) -> &'static str {
    if french() {
        fr
    } else {
        en
    }
}

fn item(app: &AppHandle, id: &str, fr: &str, en: &str) -> tauri::Result<MenuItem<tauri::Wry>> {
    MenuItem::with_id(app, id, if french() { fr } else { en }, true, None::<&str>)
}

pub struct TrayMenu {
    tray: TrayIcon<tauri::Wry>,
    status: MenuItem<tauri::Wry>,
    connect: MenuItem<tauri::Wry>,
    resume: MenuItem<tauri::Wry>,
    pause: Submenu<tauri::Wry>,
    features: Vec<CheckMenuItem<tauri::Wry>>,
    obs: CheckMenuItem<tauri::Wry>,
    autostart: CheckMenuItem<tauri::Wry>,
    last: Mutex<Option<TraySnapshot>>,
}

#[derive(PartialEq, Eq)]
struct TraySnapshot {
    status: String,
    tooltip: String,
    connected: bool,
    paused: bool,
    features: [bool; 4],
    obs: bool,
    autostart: bool,
}

impl TrayMenu {
    pub fn install(app: &AppHandle) -> tauri::Result<Self> {
        let status = item(app, "status", "Démarrage…", "Starting…")?;
        status.set_enabled(false)?;
        let open = item(app, "open", "Ouvrir 3Decks", "Open 3Decks")?;
        let connect = item(
            app,
            "connect",
            "Connecter une console…",
            "Connect a console…",
        )?;
        let resume = item(app, "resume", "Reprendre les commandes", "Resume controls")?;
        let pause = Submenu::with_id(
            app,
            "pause",
            label("Suspendre les commandes", "Suspend controls"),
            true,
        )?;
        let pause_15 = item(app, "pause.15", "Pendant 15 minutes", "For 15 minutes")?;
        let pause_60 = item(app, "pause.60", "Pendant 1 heure", "For 1 hour")?;
        let pause_until = item(app, "pause.until", "Jusqu’à réactivation", "Until resumed")?;
        pause.append_items(&[&pause_15, &pause_60, &pause_until])?;

        let quick = Submenu::with_id(
            app,
            "quick",
            label("Réglages rapides", "Quick settings"),
            true,
        )?;
        let names = [
            ("Notifications", "Notifications"),
            ("Musique et médias", "Music and media"),
            ("Fenêtres ouvertes", "Open windows"),
            ("Performances du PC", "Computer performance"),
        ];
        let mut features = Vec::new();
        for (feature, (fr, en)) in FEATURES.into_iter().zip(names) {
            let check = CheckMenuItem::with_id(
                app,
                format!("feature.{feature}"),
                if french() { fr } else { en },
                true,
                false,
                None::<&str>,
            )?;
            quick.append(&check)?;
            features.push(check);
        }
        let obs =
            CheckMenuItem::with_id(app, "feature.obs", "OBS Studio", true, false, None::<&str>)?;
        quick.append(&obs)?;
        let autostart = CheckMenuItem::with_id(
            app,
            "autostart",
            label("Lancer à l’ouverture de session", "Launch at login"),
            true,
            false,
            None::<&str>,
        )?;
        let diagnostics =
            Submenu::with_id(app, "diagnostics", label("Diagnostic", "Diagnostics"), true)?;
        let open_status = item(
            app,
            "diag.status",
            "Ouvrir l’état de l’agent",
            "Open agent status",
        )?;
        let copy_address = item(
            app,
            "diag.copy",
            "Copier l’adresse de connexion",
            "Copy connection address",
        )?;
        let open_logs = item(app, "diag.logs", "Ouvrir le journal", "Open log")?;
        let restart = item(app, "diag.restart", "Redémarrer l’agent", "Restart agent")?;
        diagnostics.append_items(&[
            &open_status,
            &copy_address,
            &open_logs,
            &PredefinedMenuItem::separator(app)?,
            &restart,
        ])?;
        let updates = item(
            app,
            "updates",
            "Rechercher une mise à jour…",
            "Check for updates…",
        )?;
        let quit = item(app, "quit", "Quitter 3Decks", "Quit 3Decks")?;
        let menu = Menu::with_items(
            app,
            &[
                &status,
                &open,
                &connect,
                &PredefinedMenuItem::separator(app)?,
                &resume,
                &pause,
                &quick,
                &PredefinedMenuItem::separator(app)?,
                &autostart,
                &diagnostics,
                &updates,
                &PredefinedMenuItem::separator(app)?,
                &quit,
            ],
        )?;
        let icon = app
            .default_window_icon()
            .expect("Tauri icon missing")
            .clone();
        let tray = TrayIconBuilder::new()
            .icon(icon)
            .menu(&menu)
            .on_menu_event(|app, event| handle(app.clone(), event.id.as_ref().to_owned()))
            .build(app)?;
        Ok(Self {
            tray,
            status,
            connect,
            resume,
            pause,
            features,
            obs,
            autostart,
            last: Mutex::new(None),
        })
    }

    pub fn refresh(&self, app: &AppHandle, shared: &Shared) {
        let status = shared.snapshot();
        let paused = shared.controls_paused();
        let text = if status.error.is_some() {
            label(
                "Agent actif · attention requise",
                "Agent running · attention required",
            )
            .to_owned()
        } else if !status.running {
            label("Démarrage de l’agent…", "Starting agent…").to_owned()
        } else if paused {
            label("Commandes suspendues", "Controls suspended").to_owned()
        } else if status.connected == 0 {
            label("Agent actif · aucune console", "Agent running · no console").to_owned()
        } else if status.connected == 1 {
            label(
                "Agent actif · 1 console connectée",
                "Agent running · 1 console connected",
            )
            .to_owned()
        } else if french() {
            format!("Agent actif · {} consoles connectées", status.connected)
        } else {
            format!("Agent running · {} consoles connected", status.connected)
        };
        let tooltip = if paused {
            label(
                "3Decks — commandes suspendues",
                "3Decks — controls suspended",
            )
            .to_owned()
        } else if status.connected == 0 {
            label("3Decks — aucune console", "3Decks — no console").to_owned()
        } else if status.connected == 1 {
            label(
                "3Decks — 1 console connectée",
                "3Decks — 1 console connected",
            )
            .to_owned()
        } else if french() {
            format!("3Decks — {} consoles connectées", status.connected)
        } else {
            format!("3Decks — {} consoles connected", status.connected)
        };
        let snapshot = TraySnapshot {
            status: text,
            tooltip,
            connected: status.connected > 0,
            paused,
            features: FEATURES.map(|feature| shared.config.feature_enabled(feature)),
            obs: shared.config.document()["integrations"]["obs"]["enabled"].as_bool() == Some(true),
            autostart: app.autolaunch().is_enabled().unwrap_or(false),
        };
        let mut last = self.last.lock().unwrap();
        if last.as_ref() == Some(&snapshot) {
            return;
        }
        let _ = self.status.set_text(&snapshot.status);
        let _ = self.tray.set_tooltip(Some(&snapshot.tooltip));
        let _ = self.connect.set_enabled(!snapshot.connected);
        let _ = self.resume.set_enabled(snapshot.paused);
        let _ = self.pause.set_enabled(!snapshot.paused);
        for (enabled, check) in snapshot.features.into_iter().zip(&self.features) {
            let _ = check.set_checked(enabled);
        }
        let _ = self.obs.set_checked(snapshot.obs);
        let _ = self.autostart.set_checked(snapshot.autostart);
        *last = Some(snapshot);
    }
}

fn handle(app: AppHandle, id: String) {
    tauri::async_runtime::spawn(async move {
        if let Err(error) = dispatch(&app, &id).await {
            logging::append(&format!("Tray action {id} failed: {error}"));
            app.dialog()
                .message(error)
                .title("3Decks")
                .kind(MessageDialogKind::Error)
                .show(|_| {});
        }
        if let (Some(menu), Some(shared)) =
            (app.try_state::<TrayMenu>(), app.try_state::<Arc<Shared>>())
        {
            menu.refresh(&app, &shared);
        }
    });
}

async fn dispatch(app: &AppHandle, id: &str) -> Result<(), String> {
    let shared = app.state::<Arc<Shared>>();
    match id {
        "open" => crate::open_editor_at(app, "").map_err(|error| error.to_string()),
        "connect" => {
            crate::open_editor_at(app, "settings/connection").map_err(|error| error.to_string())
        }
        "diag.status" => crate::open_editor_at(app, "status").map_err(|error| error.to_string()),
        "pause.15" => {
            shared.pause_controls(Some(Duration::from_secs(15 * 60)));
            logging::append("Controls paused for 15 minutes");
            Ok(())
        }
        "pause.60" => {
            shared.pause_controls(Some(Duration::from_secs(60 * 60)));
            logging::append("Controls paused for 1 hour");
            Ok(())
        }
        "pause.until" => {
            shared.pause_controls(None);
            logging::append("Controls paused until resumed");
            Ok(())
        }
        "resume" => {
            shared.resume_controls();
            logging::append("Controls resumed");
            Ok(())
        }
        "autostart" => {
            let manager = app.autolaunch();
            let enabled = manager.is_enabled().map_err(|error| error.to_string())?;
            if enabled {
                manager.disable()
            } else {
                manager.enable()
            }
            .map_err(|error| error.to_string())?;
            Ok(())
        }
        "diag.copy" => {
            let address = desktop::address_hints(shared.snapshot().tcp_port)
                .into_iter()
                .next()
                .unwrap_or_else(|| format!("127.0.0.1:{}", shared.snapshot().tcp_port));
            copy_address(&address)
        }
        "diag.logs" => {
            let path = logging::path().ok_or("Diagnostic log is unavailable")?;
            open_path(path.to_string_lossy().as_ref()).await
        }
        "diag.restart" => {
            logging::append("Restart requested from tray");
            let _ = shared.stop.send(true);
            for _ in 0..60 {
                if !shared.snapshot().running {
                    break;
                }
                tokio::time::sleep(Duration::from_millis(50)).await;
            }
            app.restart();
        }
        "updates" => open_url(RELEASES_URL).await,
        "quit" => {
            logging::append("Quit requested from tray");
            let _ = shared.stop.send(true);
            let app = app.clone();
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(Duration::from_millis(100)).await;
                app.exit(0);
            });
            Ok(())
        }
        "feature.obs" => toggle_setting(&shared, "obs"),
        value if value.starts_with("feature.") => toggle_setting(&shared, &value[8..]),
        _ => Ok(()),
    }
}

fn toggle_setting(shared: &Shared, name: &str) -> Result<(), String> {
    if name != "obs" && !FEATURES.contains(&name) {
        return Err("Unknown quick setting".into());
    }
    let mut document = shared.config.document();
    let current = if name == "obs" {
        &mut document["integrations"]["obs"]["enabled"]
    } else {
        &mut document["features"][name]
    };
    let enabled = current.as_bool().unwrap_or(false);
    *current = serde_json::json!(!enabled);
    let saved = shared.config.save(document)?;
    let revision = saved["revision"].as_u64().unwrap_or(0);
    let _ = shared.config_updates.send(revision);
    shared.update(|status| {
        status.config_revision = revision;
        status.last_event = format!(
            "Quick setting {name} {}",
            if enabled { "disabled" } else { "enabled" }
        );
    });
    Ok(())
}

#[cfg(target_os = "macos")]
fn copy_address(address: &str) -> Result<(), String> {
    use objc2_app_kit::{NSPasteboard, NSPasteboardTypeString};
    use objc2_foundation::NSString;
    let pasteboard = NSPasteboard::generalPasteboard();
    pasteboard.clearContents();
    if pasteboard.setString_forType(&NSString::from_str(address), unsafe {
        NSPasteboardTypeString
    }) {
        Ok(())
    } else {
        Err("Unable to copy the connection address".into())
    }
}

#[cfg(not(target_os = "macos"))]
fn copy_address(_address: &str) -> Result<(), String> {
    Err("Clipboard integration is not available on this platform yet".into())
}

async fn open_path(path: &str) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        crate::platform::macos::workspace::open_file(path).await
    }
    #[cfg(target_os = "windows")]
    {
        crate::platform::windows::shell::open(path).await
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = path;
        Err("Opening logs is not available on this platform yet".into())
    }
}

async fn open_url(url: &str) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        crate::platform::macos::workspace::open_web_url(url).await
    }
    #[cfg(target_os = "windows")]
    {
        crate::platform::windows::shell::open(url).await
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = url;
        Err("Opening updates is not available on this platform yet".into())
    }
}

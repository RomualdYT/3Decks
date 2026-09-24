mod app;
mod features;
mod platform;
mod transport;

use app::{config, desktop, logging, onboarding, state, tray};
use features::{artwork, obs, telemetry};
use platform::{audio, system};
use transport::{network, protocol};

use serde_json::Value;
use state::{Shared, Status};
use std::{sync::Arc, time::Duration};
use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder, WindowEvent};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt as AutostartManagerExt};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_updater::UpdaterExt;
use tauri_plugin_window_state::{
    AppHandleExt as WindowStateAppExt, StateFlags, WindowExt as WindowStateWindowExt,
};

const UPDATE_ENDPOINT: &str =
    "https://github.com/RomualdYT/3Decks/releases/latest/download/latest.json";

#[tauri::command]
fn get_status(shared: tauri::State<'_, Arc<Shared>>) -> Status {
    shared.snapshot()
}

#[tauri::command]
fn get_config(shared: tauri::State<'_, Arc<Shared>>) -> Value {
    shared.config.document()
}

#[tauri::command]
fn get_catalog(shared: tauri::State<'_, Arc<Shared>>) -> Result<Value, String> {
    desktop::catalog(&shared)
}

#[tauri::command]
fn get_editor_state(shared: tauri::State<'_, Arc<Shared>>) -> Result<Value, String> {
    desktop::state(&shared)
}

#[tauri::command]
fn validate_config(document: Value) -> Value {
    match config::validate(&document) {
        Ok(()) => serde_json::json!({"valid":true,"error":""}),
        Err(error) => serde_json::json!({"valid":false,"error":error}),
    }
}

#[tauri::command]
fn get_apps(shared: tauri::State<'_, Arc<Shared>>) -> Value {
    desktop::apps(&shared)
}

#[tauri::command]
async fn get_extensions(shared: tauri::State<'_, Arc<Shared>>) -> Result<Value, String> {
    Ok(shared.extensions.lock().await.describe())
}

#[tauri::command]
async fn manage_extension(
    app: AppHandle,
    shared: tauri::State<'_, Arc<Shared>>,
    mut request: Value,
) -> Result<Value, String> {
    if request["operation"] == "install" {
        let (send, receive) = tokio::sync::oneshot::channel();
        app.dialog()
            .file()
            .add_filter("3Decks extensions", &["3deckext", "zip"])
            .pick_file(move |path| {
                let _ = send.send(path);
            });
        let selected = receive.await.map_err(|error| error.to_string())?;
        let Some(selected) = selected else {
            return Ok(serde_json::json!({"cancelled":true}));
        };
        let path = selected
            .as_path()
            .ok_or("Import requires a local archive")?;
        request["path"] = serde_json::json!(path.to_string_lossy());
    }
    let mut host = shared.extensions.lock().await;
    let result = host.manage(request).await?;
    *shared.extension_catalog.write().unwrap() = host.catalog();
    *shared.extension_snapshots.write().unwrap() = host.snapshots();
    let _ = shared
        .config_updates
        .send(shared.snapshot().config_revision);
    Ok(result)
}

#[tauri::command]
fn rotate_pairing(shared: tauri::State<'_, Arc<Shared>>) -> Value {
    let code = shared.rotate_pairing();
    serde_json::json!({"required":true,"code":code,"expires_in":0})
}

#[tauri::command]
fn revoke_paired_device(
    shared: tauri::State<'_, Arc<Shared>>,
    device_id: String,
) -> Result<Value, String> {
    Ok(serde_json::json!({"revoked":shared.revoke_device(&device_id)?}))
}

#[tauri::command]
fn save_config(shared: tauri::State<'_, Arc<Shared>>, document: Value) -> Result<Value, String> {
    let saved = shared.config.save(document)?;
    let revision = saved["revision"].as_u64().unwrap_or(0);
    let _ = shared.config_updates.send(revision);
    shared.update(|s| {
        s.config_revision = revision;
        s.last_event = format!("Configuration saved (revision {revision})");
    });
    Ok(saved)
}

#[tauri::command]
async fn get_obs_status(shared: tauri::State<'_, Arc<Shared>>) -> Result<Value, String> {
    let config = obs::ObsConfig::from_document(&shared.config.document())?;
    obs::status(&config).await
}

#[tauri::command]
async fn test_obs(config: Value) -> Result<Value, String> {
    let settings =
        obs::ObsConfig::from_document(&serde_json::json!({"integrations":{"obs":config}}))?;
    obs::status(&settings).await
}

#[tauri::command]
async fn get_audio_outputs() -> Result<Vec<audio::Output>, String> {
    audio::outputs().await
}

#[tauri::command]
async fn select_audio_output(name: String) -> Result<String, String> {
    audio::select(&name).await
}

#[tauri::command]
fn get_artwork(shared: tauri::State<'_, Arc<Shared>>) -> Option<Vec<u8>> {
    shared.artwork.lock().unwrap().preview()
}

#[tauri::command]
fn get_onboarding(shared: tauri::State<'_, Arc<Shared>>) -> onboarding::Progress {
    shared.onboarding.read()
}

#[tauri::command]
fn save_onboarding(
    shared: tauri::State<'_, Arc<Shared>>,
    step: u8,
    completed: bool,
) -> Result<onboarding::Progress, String> {
    shared.onboarding.save(step, completed)
}

#[tauri::command]
fn get_permission_status(shared: tauri::State<'_, Arc<Shared>>) -> Value {
    #[cfg(target_os = "macos")]
    let accessibility = {
        #[link(name = "ApplicationServices", kind = "framework")]
        unsafe extern "C" {
            fn AXIsProcessTrusted() -> bool;
        }
        unsafe { AXIsProcessTrusted() }
    };
    #[cfg(not(target_os = "macos"))]
    let accessibility = false;
    serde_json::json!({
        "platform": if cfg!(target_os = "macos") { "darwin" } else if cfg!(target_os = "windows") { "win32" } else { "linux" },
        "local_network": shared.snapshot().running,
        "accessibility": accessibility,
        "notifications": shared.notifications.lock().unwrap().status(),
        "automation": "prompt_on_use",
    })
}

#[tauri::command]
fn get_autostart(app: AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .is_enabled()
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn set_autostart(app: AppHandle, enabled: bool) -> Result<bool, String> {
    if enabled {
        app.autolaunch().enable()
    } else {
        app.autolaunch().disable()
    }
    .map_err(|error| error.to_string())?;
    app.autolaunch()
        .is_enabled()
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn get_update_capability(app: AppHandle) -> Value {
    serde_json::json!({"configured": option_env!("DECKS_UPDATER_PUBKEY").is_some(), "version": app.package_info().version.to_string()})
}

async fn available_update(app: &AppHandle) -> Result<Option<tauri_plugin_updater::Update>, String> {
    let key = option_env!("DECKS_UPDATER_PUBKEY")
        .ok_or("Les mises à jour signées ne sont pas configurées pour ce build")?;
    let endpoint = url::Url::parse(UPDATE_ENDPOINT).map_err(|error| error.to_string())?;
    app.updater_builder()
        .pubkey(key)
        .endpoints(vec![endpoint])
        .map_err(|error| error.to_string())?
        .build()
        .map_err(|error| error.to_string())?
        .check()
        .await
        .map_err(|error| error.to_string())
}

#[tauri::command]
async fn check_for_updates(app: AppHandle) -> Result<Value, String> {
    let available = available_update(&app).await?;
    Ok(match available {
        Some(update) => {
            serde_json::json!({"available":true,"version":update.version,"notes":update.body})
        }
        None => {
            serde_json::json!({"available":false,"version":app.package_info().version.to_string()})
        }
    })
}

#[tauri::command]
async fn install_update(app: AppHandle) -> Result<(), String> {
    let update = available_update(&app)
        .await?
        .ok_or("Aucune nouvelle version disponible")?;
    update
        .download_and_install(|_, _| {}, || {})
        .await
        .map_err(|error| error.to_string())?;
    app.restart();
}

#[tauri::command]
async fn open_permission_settings(permission: String) -> Result<Value, String> {
    #[cfg(target_os = "macos")]
    {
        let pane = match permission.as_str() {
            "notifications" => {
                "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
            }
            "accessibility" => {
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
            }
            "automation" => {
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation"
            }
            _ => return Err("Unknown permission".into()),
        };
        let status = tokio::process::Command::new("/usr/bin/open")
            .arg(pane)
            .status()
            .await
            .map_err(|error| error.to_string())?;
        if !status.success() {
            return Err("Unable to open macOS privacy settings".into());
        }
        Ok(serde_json::json!({"opened":true,"permission":permission}))
    }
    #[cfg(not(target_os = "macos"))]
    {
        Err(format!(
            "Permission settings are not implemented for {permission} on this platform"
        ))
    }
}

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .plugin(tauri_plugin_autostart::init(
            MacosLauncher::LaunchAgent,
            Some(vec!["--tray-only"]),
        ))
        .setup(|app| {
            logging::init(app.handle()).map_err(std::io::Error::other)?;
            if let Some(key) = option_env!("DECKS_UPDATER_PUBKEY") {
                app.handle()
                    .plugin(tauri_plugin_updater::Builder::new().pubkey(key).build())?;
            }
            let tcp_port = port_from_env("DECKS_POC_TCP_PORT", 38123);
            let discovery_port = port_from_env("DECKS_POC_DISCOVERY_PORT", 38122);
            let shared = Arc::new(
                Shared::new(app.handle().clone(), tcp_port, discovery_port)
                    .map_err(std::io::Error::other)?,
            );
            app.manage(shared.clone());
            let tray_menu = tray::TrayMenu::install(app.handle())?;
            tray_menu.refresh(app.handle(), &shared);
            app.manage(tray_menu);
            if std::env::var("DECKS_POC_START_TRAY_ONLY").as_deref() != Ok("1")
                && !std::env::args().any(|arg| arg == "--tray-only")
            {
                open_editor(app.handle())?;
            }
            tauri::async_runtime::spawn(async move {
                if let Err(error) = network::run(shared.clone()).await {
                    shared.update(|s| {
                        s.running = false;
                        s.error = Some(error);
                        s.last_event = "Server unavailable".into();
                    });
                }
            });
            let menu_app = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                loop {
                    tokio::time::sleep(Duration::from_secs(1)).await;
                    let Some(shared) = menu_app.try_state::<Arc<Shared>>() else {
                        break;
                    };
                    let Some(menu) = menu_app.try_state::<tray::TrayMenu>() else {
                        break;
                    };
                    menu.refresh(&menu_app, &shared);
                }
            });
            #[cfg(debug_assertions)]
            if let Ok(milliseconds) = std::env::var("DECKS_POC_TEST_CLOSE_AFTER_MS")
                .unwrap_or_default()
                .parse::<u64>()
            {
                let handle = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    tokio::time::sleep(Duration::from_millis(milliseconds)).await;
                    if let Some(window) = handle.get_webview_window("main") {
                        let _ = window.destroy();
                    }
                });
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.app_handle().save_window_state(StateFlags::all());
                let _ = window.destroy();
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_status,
            get_config,
            get_catalog,
            get_editor_state,
            validate_config,
            get_apps,
            get_extensions,
            manage_extension,
            rotate_pairing,
            revoke_paired_device,
            save_config,
            get_obs_status,
            test_obs,
            get_audio_outputs,
            select_audio_output,
            get_artwork,
            get_onboarding,
            save_onboarding,
            get_permission_status,
            open_permission_settings,
            get_autostart,
            set_autostart,
            get_update_capability,
            check_for_updates,
            install_update
        ])
        .build(tauri::generate_context!())
        .expect("3Decks PoC failed to start");
    app.run(|_app, event| {
        if let RunEvent::ExitRequested {
            code: None, api, ..
        } = event
        {
            api.prevent_exit();
        }
    });
}

fn open_editor(app: &AppHandle) -> tauri::Result<()> {
    open_editor_at(app, "")
}

pub(crate) fn open_editor_at(app: &AppHandle, route: &str) -> tauri::Result<()> {
    let existing = app.get_webview_window("main").is_some();
    let window = if let Some(window) = app.get_webview_window("main") {
        window
    } else {
        let (width, height) = app
            .primary_monitor()?
            .map(|monitor| {
                let size = monitor.size().to_logical::<f64>(monitor.scale_factor());
                (
                    (size.width * 0.92).min(1440.0).max(980.0),
                    (size.height * 0.88).min(900.0).max(700.0),
                )
            })
            .unwrap_or((1360.0, 820.0));
        let page = if route.is_empty() {
            "index.html".to_owned()
        } else {
            format!("index.html#{route}")
        };
        let mut builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::App(page.into()))
            .title("3Decks")
            .inner_size(width, height)
            .min_inner_size(980.0, 700.0)
            .center()
            .visible(false);
        #[cfg(target_os = "macos")]
        {
            builder = builder
                .title("")
                .title_bar_style(tauri::TitleBarStyle::Overlay)
                .traffic_light_position(tauri::LogicalPosition::new(17.0, 20.0));
        }
        let window = builder.build()?;
        let _ = window.restore_state(StateFlags::all());
        window
    };
    if existing && !route.is_empty() {
        window.eval(format!("window.location.hash = '#{route}'"))?;
    }
    window.show()?;
    window.set_focus()?;
    Ok(())
}

fn port_from_env(key: &str, default: u16) -> u16 {
    std::env::var(key)
        .ok()
        .and_then(|value| value.parse::<u16>().ok())
        .filter(|port| *port >= 1024)
        .unwrap_or(default)
}

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

/// Open the bundled invitation with the system browser, never inside the webview.
#[tauri::command]
async fn open_community() -> Result<(), String> {
    let community: Value = serde_json::from_str(include_str!("../../../../resources/community.json"))
        .map_err(|error| error.to_string())?;
    let url = community["invite_url"].as_str().ok_or("Missing community invitation")?;
    #[cfg(target_os = "windows")]
    { return platform::windows::shell::open(url).await; }
    #[cfg(not(target_os = "windows"))]
    {
        #[cfg(target_os = "macos")]
        let program = "/usr/bin/open";
        #[cfg(not(target_os = "macos"))]
        let program = "xdg-open";
        let status = tokio::process::Command::new(program).arg(url).status().await
            .map_err(|error| error.to_string())?;
        if status.success() { Ok(()) } else { Err("Unable to open community invitation".into()) }
    }
}

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
async fn get_apps(shared: tauri::State<'_, Arc<Shared>>) -> Result<Value, String> {
    let result = desktop::apps(&shared);
    #[cfg(any(target_os = "windows", target_os = "macos"))]
    {
        let mut names: Vec<String> = result["apps"].as_array().unwrap().iter()
            .filter_map(|name| name.as_str().map(str::to_owned)).collect();
        #[cfg(target_os = "windows")]
        names.extend(platform::windows::applications::names().await);
        #[cfg(target_os = "macos")]
        names.extend(platform::macos::applications::names().await);
        names.sort_by_key(|name| name.to_lowercase());
        names.dedup();
        return Ok(serde_json::json!({"apps": names}));
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    Ok(result)
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
    shared.publish_extensions(host.catalog(), host.snapshots());
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
fn get_stream_chat(shared: tauri::State<'_, Arc<Shared>>) -> features::stream_chat::View {
    shared.stream_chat.view()
}

#[tauri::command]
fn configure_stream_chat(shared: tauri::State<'_, Arc<Shared>>, settings: features::stream_chat::Settings) -> Result<features::stream_chat::View, String> {
    shared.stream_chat.configure(settings)
}

#[tauri::command]
async fn authorize_stream_chat(shared: tauri::State<'_, Arc<Shared>>) -> Result<features::stream_chat::View, String> {
    shared.stream_chat.authorize().await
}

#[tauri::command]
async fn disconnect_stream_chat(shared: tauri::State<'_, Arc<Shared>>) -> Result<features::stream_chat::View, String> {
    shared.stream_chat.disconnect().await
}

#[tauri::command]
async fn open_stream_chat_authorization(shared: tauri::State<'_, Arc<Shared>>) -> Result<(), String> {
    let authorization = shared.stream_chat.view().authorization.ok_or("authorization_expired")?;
    // The backend validates the Twitch activation URL before exposing it.
    system::perform(&serde_json::json!({"type":"url.open", "url":authorization.url}), 5).await?;
    Ok(())
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
async fn select_audio_output(id: String) -> Result<String, String> {
    audio::select(&id).await
}

#[tauri::command]
async fn open_audio_settings() -> Result<(), String> {
    audio::open_settings().await
}

#[tauri::command]
async fn request_notification_access(
    app: AppHandle,
    shared: tauri::State<'_, Arc<Shared>>,
) -> Result<Value, String> {
    #[cfg(target_os = "windows")]
    {
        let result = platform::windows::notifications::request_access_on_ui(&app).await?;
        let status = tokio::task::spawn_blocking(platform::windows::notifications::status)
            .await
            .map_err(|error| error.to_string())?;
        shared
            .notifications
            .lock()
            .unwrap()
            .set_status(status.clone());
        return Ok(serde_json::json!({"access":result,"status":status}));
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = (app, shared);
        Err("Notification access prompts are only implemented on Windows".into())
    }
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
        #[cfg(target_os = "windows")]
        {
            if permission != "notifications" {
                return Err(format!(
                    "Permission settings are not implemented for {permission}"
                ));
            }
            platform::windows::shell::open("ms-settings:notifications").await?;
            Ok(serde_json::json!({"opened":true,"permission":permission}))
        }
        #[cfg(not(target_os = "windows"))]
        Err(format!(
            "Permission settings are not implemented for {permission} on this platform"
        ))
    }
}

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_window_state::Builder::default()
            .with_state_flags(if cfg!(target_os = "windows") {
                StateFlags::all().difference(StateFlags::DECORATIONS)
            } else {
                StateFlags::all()
            })
            .build())
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
            let tcp_port = port_from_env("DECKS_TCP_PORT", 38123);
            let discovery_port = port_from_env("DECKS_DISCOVERY_PORT", 38122);
            let shared = Arc::new(
                Shared::new(app.handle().clone(), tcp_port, discovery_port)
                    .map_err(std::io::Error::other)?,
            );
            app.manage(shared.clone());
            let chat = shared.stream_chat.clone();
            let chat_stop = shared.stop.subscribe();
            tauri::async_runtime::spawn(async move { chat.run(chat_stop).await; });
            let tray_menu = tray::TrayMenu::install(app.handle())?;
            tray_menu.refresh(app.handle(), &shared);
            app.manage(tray_menu);
            if std::env::var("DECKS_START_TRAY_ONLY").as_deref() != Ok("1")
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
            if let Ok(milliseconds) = std::env::var("DECKS_TEST_CLOSE_AFTER_MS")
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
            open_community,
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
            get_stream_chat,
            configure_stream_chat,
            authorize_stream_chat,
            disconnect_stream_chat,
            open_stream_chat_authorization,
            get_obs_status,
            test_obs,
            get_audio_outputs,
            select_audio_output,
            open_audio_settings,
            request_notification_access,
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
        .expect("3Decks failed to start");
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
    let existing_window = app.get_webview_window("main");
    let existing = existing_window.is_some();
    let window = if let Some(window) = existing_window {
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
                // Wry's vertical inset places the native control centers near y=36,
                // aligned with the 72 px editor toolbar.
                .traffic_light_position(tauri::LogicalPosition::new(18.0, 32.0));
        }
        #[cfg(target_os = "windows")]
        {
            builder = builder.decorations(false).shadow(true);
        }
        let window = builder.build()?;
        let restore_flags = StateFlags::all();
        #[cfg(target_os = "windows")]
        let restore_flags = restore_flags.difference(StateFlags::DECORATIONS);
        let _ = window.restore_state(restore_flags);
        // Old sessions may have been saved with the native Windows titlebar.
        #[cfg(target_os = "windows")]
        window.set_decorations(false)?;
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

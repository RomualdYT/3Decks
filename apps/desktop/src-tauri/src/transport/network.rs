use crate::features::lyrics;
use crate::platform::windowing;
use crate::{artwork, audio, obs, protocol, state::Shared, system, telemetry};
use serde_json::{json, Value};
use std::{
    net::{Ipv4Addr, SocketAddr},
    sync::Arc,
    time::Duration,
};
use tokio::{
    net::{TcpListener, TcpStream, UdpSocket},
    sync::{watch, Semaphore},
    time::timeout,
};

const MULTICAST: Ipv4Addr = Ipv4Addr::new(239, 255, 77, 83);
const MAX_DATAGRAM: usize = 512;
const MAX_PENDING: usize = 16;
const MAX_AUTHENTICATED: usize = 8;

pub async fn run(shared: Arc<Shared>) -> Result<(), String> {
    // Bind both sockets before announcing readiness. Alternate ports allow coexistence with Python.
    let status = shared.snapshot();
    let tcp_port = status.tcp_port;
    let discovery_port = status.discovery_port;
    let tcp = TcpListener::bind(("0.0.0.0", tcp_port))
        .await
        .map_err(|e| format!("TCP {tcp_port}: {e}"))?;
    let udp = UdpSocket::bind(("0.0.0.0", discovery_port))
        .await
        .map_err(|e| format!("UDP {discovery_port}: {e}"))?;
    udp.set_broadcast(true).map_err(|e| e.to_string())?;
    // Broadcast/manual address still work if joining this group is unavailable.
    let multicast_error = udp
        .join_multicast_v4(MULTICAST, Ipv4Addr::UNSPECIFIED)
        .err();
    shared.update(|s| {
        s.running = true;
        s.error = None;
        s.last_event = match multicast_error {
            Some(error) => format!("Ready; multicast unavailable: {error}"),
            None => "Ready for Nintendo 3DS discovery".into(),
        };
    });

    let mut stop = shared.stop.subscribe();
    let lyrics_shared = shared.clone();
    let lyrics_task = tokio::spawn(async move { lyrics::run(lyrics_shared).await });
    let udp_shared = shared.clone();
    let udp_stop = shared.stop.subscribe();
    let udp_task = tokio::spawn(async move { discovery_loop(udp, udp_shared, udp_stop).await });
    let state_shared = shared.clone();
    let mut state_stop = shared.stop.subscribe();
    let state_task = tokio::spawn(async move {
        loop {
            tokio::select! {
                changed = state_stop.changed() => { if changed.is_err() || *state_stop.borrow() { break; } }
                _ = tokio::time::sleep(state_shared.config.poll_interval()) => {
                    let snapshot = collect_state(&state_shared).await;
                    let volume = snapshot["volume"].as_u64().map(|value| value as u8);
                    let cpu = snapshot["cpu"].as_u64().map(|value| value as u8);
                    let memory = snapshot["memory"].as_u64().map(|value| value as u8);
                    state_shared.update(|status| { status.volume = volume; status.cpu = cpu; status.memory = memory; });
                    let _ = state_shared.state_updates.send(snapshot);
                }
            }
        }
    });
    let extension_shared = shared.clone();
    let mut extension_stop = shared.stop.subscribe();
    let extension_task = tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_millis(500));
        loop {
            tokio::select! {
                _ = interval.tick() => {
                    let mut host = extension_shared.extensions.lock().await;
                    host.poll_all().await;
                    let catalog = host.catalog();
                    let snapshots = host.snapshots();
                    let changed = *extension_shared.extension_catalog.read().unwrap() != catalog
                        || *extension_shared.extension_snapshots.read().unwrap() != snapshots;
                    *extension_shared.extension_catalog.write().unwrap() = catalog;
                    *extension_shared.extension_snapshots.write().unwrap() = snapshots;
                    if changed { let _ = extension_shared.config_updates.send(extension_shared.snapshot().config_revision); }
                }
                changed = extension_stop.changed() => { if changed.is_err() || *extension_stop.borrow() { break; } }
            }
        }
    });
    let window_shared = shared.clone();
    let mut window_stop = shared.stop.subscribe();
    let window_task = tokio::spawn(async move {
        let mut tick = tokio::time::interval(Duration::from_secs(3));
        loop {
            tokio::select! {
                changed = window_stop.changed() => { if changed.is_err() || *window_stop.borrow() { break; } }
                _ = tick.tick() => {
                    let windows = if window_shared.config.feature_enabled("windows") { windowing::list().await } else { vec![] };
                    let mut current = window_shared.windows.write().unwrap();
                    if *current != windows {
                        let count = windows.len();
                        *current = windows;
                        drop(current);
                        window_shared.update(|status| status.windows_count = count);
                        let _ = window_shared.config_updates.send(window_shared.snapshot().config_revision);
                    }
                }
            }
        }
    });
    let pending = Arc::new(Semaphore::new(MAX_PENDING));
    let authenticated = Arc::new(Semaphore::new(MAX_AUTHENTICATED));

    loop {
        tokio::select! {
            changed = stop.changed() => {
                if changed.is_err() || *stop.borrow() { break; }
            }
            accepted = tcp.accept() => {
                let (stream, address) = accepted.map_err(|e| e.to_string())?;
                let Ok(pending_slot) = pending.clone().try_acquire_owned() else {
                    tokio::spawn(async move { let mut stream = stream; let _ = protocol::write(&mut stream, &json!({"type":"hello.error","reason":"server busy","code":"server_busy"})).await; });
                    continue;
                };
                let shared = shared.clone();
                let authenticated = authenticated.clone();
                let stop = shared.stop.subscribe();
                tokio::spawn(async move {
                    if let Err(error) = serve(stream, address, shared.clone(), authenticated, stop, pending_slot).await {
                        shared.update(|s| s.last_event = format!("{address}: {error}"));
                    }
                });
            }
        }
    }
    let _ = udp_task.await;
    let _ = state_task.await;
    let _ = extension_task.await;
    let _ = lyrics_task.await;
    let _ = window_task.await;
    shared.update(|s| {
        s.running = false;
        s.connected = 0;
        s.last_event = "Stopped".into();
    });
    Ok(())
}

async fn discovery_loop(socket: UdpSocket, shared: Arc<Shared>, mut stop: watch::Receiver<bool>) {
    let mut buffer = [0_u8; MAX_DATAGRAM + 1];
    loop {
        tokio::select! {
            changed = stop.changed() => {
                if changed.is_err() || *stop.borrow() { return; }
            }
            received = socket.recv_from(&mut buffer) => {
                let Ok((size, peer)) = received else { continue; };
                if size == 0 || size > MAX_DATAGRAM { continue; }
                let Ok(value) = serde_json::from_slice::<Value>(&buffer[..size]) else { continue; };
                if value.get("type").and_then(Value::as_str) != Some("deck3ds.discover")
                    || value.get("protocol").and_then(Value::as_u64) != Some(1) { continue; }
                let mut reply = json!({
                    "type": "deck3ds.agent", "protocol": 1,
                    "name": "3Decks", "platform": platform_name(),
                    "port": shared.snapshot().tcp_port, "version": env!("CARGO_PKG_VERSION"), "pairing_required": true
                });
                if let Some(nonce) = value.get("nonce").and_then(Value::as_i64) {
                    reply["nonce"] = json!(nonce);
                }
                if let Ok(bytes) = serde_json::to_vec(&reply) {
                    let _ = socket.send_to(&bytes, peer).await;
                    shared.update(|s| s.last_event = format!("Discovery from {}", peer.ip()));
                }
            }
        }
    }
}

async fn serve(
    mut stream: TcpStream,
    address: SocketAddr,
    shared: Arc<Shared>,
    authenticated: Arc<Semaphore>,
    mut stop: watch::Receiver<bool>,
    pending_slot: tokio::sync::OwnedSemaphorePermit,
) -> Result<(), String> {
    stream.set_nodelay(true).map_err(|e| e.to_string())?;
    let hello = timeout(Duration::from_secs(5), protocol::read(&mut stream))
        .await
        .map_err(|_| "handshake timeout".to_string())??;
    if hello.get("type").and_then(Value::as_str) != Some("hello")
        || hello.get("protocol").and_then(Value::as_u64) != Some(1)
    {
        let _ = protocol::write(
            &mut stream,
            &json!({"type":"hello.error","reason":"incompatible protocol"}),
        )
        .await;
        return Err("incompatible handshake".into());
    }
    let device = hello.get("device").and_then(Value::as_str).unwrap_or("3DS");
    if device.len() > 64 {
        return Err("device name too long".into());
    }
    let Ok(auth_slot) = authenticated.try_acquire_owned() else {
        let _ = protocol::write(
            &mut stream,
            &json!({"type":"hello.error","reason":"server busy","code":"server_busy"}),
        )
        .await;
        return Err("authenticated console limit reached".into());
    };
    let auth = shared.authenticate(
        hello.get("token").and_then(Value::as_str),
        hello.get("pair_code").and_then(Value::as_str),
        device,
        address.ip(),
    );
    let issued = match auth {
        Ok(issued) => issued,
        Err(code) => {
            let _ = protocol::write(
                &mut stream,
                &json!({"type":"hello.error","reason":"pairing required","code":code}),
            )
            .await;
            return Err(code.into());
        }
    };
    drop(pending_slot);
    let mut hello_ok = json!({"type":"hello.ok","protocol":1,"agent":env!("CARGO_PKG_VERSION"),"host":"3Decks","platform":platform_name()});
    if let Some(token) = issued {
        hello_ok["token"] = json!(token);
    }
    protocol::write(&mut stream, &hello_ok).await?;
    let locale = match hello.get("language").and_then(Value::as_str) {
        Some("fr") => "fr",
        _ => "en",
    };
    protocol::write(&mut stream, &shared.config_snapshot(locale)).await?;
    let initial = collect_state(&shared).await;
    protocol::write(&mut stream, &initial).await?;
    let lyrics = shared.latest_lyrics.read().unwrap().clone();
    protocol::write(&mut stream, &lyrics).await?;
    let mut last_art_token = 0;
    write_art_if_changed(&mut stream, &shared, &initial, &mut last_art_token).await?;
    let client_id = shared.client_connected(device, &address.to_string());
    let mut last_mutation: Option<u64> = None;
    let mut config_updates = shared.config_updates.subscribe();
    let mut state_updates = shared.state_updates.subscribe();
    let mut lyrics_updates = shared.lyrics_updates.subscribe();
    let mut revoked = shared.revoked.subscribe();
    let result = loop {
        let message = tokio::select! {
            changed = stop.changed() => {
                if changed.is_err() || *stop.borrow() { break Ok(()); }
                continue;
            }
            revoked_name = revoked.recv() => {
                if revoked_name.as_deref() == Ok(device) { break Err("Console access revoked".into()); }
                continue;
            }
            read = protocol::read(&mut stream) => match read { Ok(value) => value, Err(e) => break Err(e) },
            changed = config_updates.changed() => {
                if changed.is_ok() {
                    if let Err(error) = protocol::write(&mut stream, &shared.config_snapshot(locale)).await { break Err(error); }
                    continue;
                }
                continue;
            }
            update = state_updates.recv() => {
                if let Ok(update) = update {
                    if let Err(error) = protocol::write(&mut stream, &update).await { break Err(error); }
                    if let Err(error) = write_art_if_changed(&mut stream, &shared, &update, &mut last_art_token).await { break Err(error); }
                }
                continue;
            }
            update = lyrics_updates.recv() => {
                if let Ok(update) = update {
                    if let Err(error) = protocol::write(&mut stream, &update).await { break Err(error); }
                }
                continue;
            }
        };
        let kind = message.get("type").and_then(Value::as_str);
        let response = match kind {
            Some("ping") => Some(
                json!({"type":"pong","id":message.get("id").and_then(Value::as_u64).unwrap_or(0)}),
            ),
            Some("config.request") => Some(shared.config_snapshot(locale)),
            Some("button.press") | Some("value.set") | Some("audio.output.select") => {
                let id = message.get("id").and_then(Value::as_u64);
                match id {
                    None => Some(action_result(0, false, "Invalid request ID")),
                    Some(id) if last_mutation.is_some_and(|previous| id <= previous) => {
                        Some(action_result(id, false, "Request already processed"))
                    }
                    Some(id) => {
                        last_mutation = Some(id);
                        let _action_slot =
                            shared.actions.acquire().await.map_err(|e| e.to_string())?;
                        let outcome = if shared.controls_paused() {
                            Err("Controls are paused from the desktop menu".into())
                        } else if kind == Some("value.set") {
                            perform_value(&shared, &message)
                                .await
                                .map(|note| (note, None))
                        } else if kind == Some("audio.output.select") {
                            if !shared.config.feature_enabled("audio_output") {
                                Err("Audio output feature is disabled".into())
                            } else {
                                match message.get("output").and_then(Value::as_str) {
                                    Some(token) => audio::select_token(token)
                                        .await
                                        .map(|_| ("Audio output changed", None)),
                                    None => Err("Audio output identifier missing".into()),
                                }
                            }
                        } else {
                            perform_button(&shared, &message).await
                        };
                        if outcome.is_ok() {
                            let shared = shared.clone();
                            tokio::spawn(async move {
                                let _ = shared.state_updates.send(collect_state(&shared).await);
                            });
                        }
                        Some(match outcome {
                            Ok((note, flag)) => {
                                let mut result = action_result(id, true, note);
                                if let Some(flag) = flag {
                                    result[flag] = json!(true);
                                }
                                result
                            }
                            Err(note) => action_result(id, false, &note),
                        })
                    }
                }
            }
            Some("hello") => break Err("duplicate handshake".into()),
            _ => None,
        };
        if let Some(response) = response {
            if let Err(e) = protocol::write(&mut stream, &response).await {
                break Err(e);
            }
        }
    };
    drop(auth_slot);
    shared.client_disconnected(client_id, device);
    result
}

async fn perform_button(
    shared: &Shared,
    message: &Value,
) -> Result<(&'static str, Option<&'static str>), String> {
    let page = message.get("page").and_then(Value::as_str);
    let button = message.get("button").and_then(Value::as_str);
    match (page, button) {
        (Some("__direct"), Some("volume.up")) => {
            system::change_volume(1, shared.config.volume_step())
                .await
                .map(|note| (note, None))
        }
        (Some("__direct"), Some("volume.down")) => {
            system::change_volume(-1, shared.config.volume_step())
                .await
                .map(|note| (note, None))
        }
        (Some("__direct"), Some("volume.mute_toggle")) => {
            system::perform(&json!("volume.mute_toggle"), shared.config.volume_step())
                .await
                .map(|note| (note, None))
        }
        (Some("__direct"), Some("mic.mute_toggle")) => {
            system::perform(&json!("mic.mute_toggle"), shared.config.volume_step())
                .await
                .map(|note| (note, None))
        }
        (Some("__direct"), Some("audio_output.cycle"))
            if shared.config.feature_enabled("audio_output") =>
        {
            audio::cycle().await.map(|_| ("Audio output changed", None))
        }
        (Some("__direct"), _) => Err("Direct action unavailable".into()),
        (Some(page), Some(button)) => {
            if let Some(window) = shared.dynamic_window(page, button) {
                return windowing::focus(&window).await.map(|note| (note, None));
            }
            let hold = message
                .get("hold")
                .and_then(Value::as_bool)
                .unwrap_or(false);
            let action = shared
                .dynamic_extension_action(page, button)
                .or_else(|| shared.config.resolve(page, button, hold))
                .ok_or("Unknown button")?;
            let kind = action
                .as_str()
                .or_else(|| action["type"].as_str())
                .unwrap_or("");
            match kind {
                "modal.volumes" => Ok(("Volumes", Some("open_modal"))),
                "settings.open" => Ok(("Settings", Some("open_settings"))),
                "frame.toggle" => Ok(("Frame", Some("toggle_frame"))),
                kind if kind.starts_with("media.") && !shared.config.feature_enabled("media") => {
                    Err("Media feature is disabled".into())
                }
                kind if kind.starts_with("app_volume.")
                    && !shared.config.feature_enabled("media") =>
                {
                    Err("Media feature is disabled".into())
                }
                "window.focus" => {
                    let app = action["app"].as_str().ok_or("Window app missing")?;
                    let title = action["title"].as_str().unwrap_or("");
                    let window = shared
                        .windows
                        .read()
                        .unwrap()
                        .iter()
                        .find(|window| {
                            window.app == app && (title.is_empty() || window.title == title)
                        })
                        .cloned()
                        .ok_or("Window not found")?;
                    windowing::focus(&window).await.map(|note| (note, None))
                }
                kind if kind.starts_with("audio_output.")
                    && !shared.config.feature_enabled("audio_output") =>
                {
                    Err("Audio output feature is disabled".into())
                }
                "audio_output.cycle" => {
                    audio::cycle().await.map(|_| ("Audio output changed", None))
                }
                "audio_output.set" => audio::select(
                    action["target"]
                        .as_str()
                        .ok_or("Audio output target missing")?,
                )
                .await
                .map(|_| ("Audio output changed", None)),
                kind if kind.starts_with("obs.") => {
                    let config = obs::ObsConfig::from_document(&shared.config.document())?;
                    obs::perform(&config, &action)
                        .await
                        .map(|note| (note, None))
                }
                kind if kind.starts_with("ext:") => {
                    let arguments = action
                        .get("arguments")
                        .filter(|value| value.is_object())
                        .cloned()
                        .unwrap_or_else(|| {
                            Value::Object(
                                action
                                    .as_object()
                                    .into_iter()
                                    .flat_map(|object| object.iter())
                                    .filter(|(key, _)| key.as_str() != "type")
                                    .map(|(key, value)| (key.clone(), value.clone()))
                                    .collect(),
                            )
                        });
                    shared
                        .extensions
                        .lock()
                        .await
                        .execute(kind, &arguments)
                        .await
                        .map(|_| ("Extension action complete", None))
                }
                _ => system::perform(&action, shared.config.volume_step())
                    .await
                    .map(|note| (note, None)),
            }
        }
        _ => Err("Invalid button request".into()),
    }
}

async fn collect_state(shared: &Shared) -> Value {
    let art_enabled = shared.config.feature_enabled("media_artwork");
    let snapshot =
        system::state_snapshot(shared.config.feature_enabled("media"), art_enabled).await;
    let mut state = snapshot.state;
    let artwork_bytes = snapshot.artwork_bytes;
    let artwork_key = snapshot.artwork_key;
    let art_url = state["media"]["art_url"].as_str().unwrap_or("").to_owned();
    if let Some(media) = state["media"].as_object_mut() {
        media.remove("art_url");
    }
    if let (Some(key), Some(bytes)) = (artwork_key.filter(|_| art_enabled), artwork_bytes) {
        artwork::refresh_bytes(shared.artwork.clone(), &key, &bytes).await;
    } else {
        artwork::refresh(
            shared.artwork.clone(),
            if art_enabled { &art_url } else { "" },
        )
        .await;
    }
    if state["media"].is_object() {
        shared.artwork.lock().unwrap().decorate(&mut state["media"]);
    }
    let notifications = shared.notifications.clone();
    let enabled = shared.config.feature_enabled("notifications");
    if let Ok(update) =
        tokio::task::spawn_blocking(move || notifications.lock().unwrap().read(enabled)).await
    {
        state["notification_count"] = json!(update.count);
        state["notifications"] = json!(update.notifications);
        if let Some(newest) = update.newest {
            state["notification_new"] = newest;
        }
    }
    state["audio_output"] = json!("");
    state["audio_output_mode"] = json!("unavailable");
    state["audio_output_count"] = json!(0);
    state["audio_output_options"] = json!([]);
    if shared.config.feature_enabled("audio_output") {
        if let Ok(outputs) = audio::outputs().await {
            if let Some(current) = outputs.iter().find(|output| output.is_default) {
                state["audio_output"] = json!(current.name);
            }
            let mut visible = outputs.iter().take(12).collect::<Vec<_>>();
            if !visible.iter().any(|output| output.is_default) {
                if let Some(current) = outputs.iter().find(|output| output.is_default) {
                    if visible.len() == 12 {
                        visible.pop();
                    }
                    visible.push(current);
                }
            }
            state["audio_output_mode"] = json!(if cfg!(target_os = "macos") {
                "direct"
            } else {
                "host_only"
            });
            state["audio_output_count"] = json!(outputs.len());
            state["audio_output_options"] = json!(visible
                .iter()
                .map(|output| json!({
                    "id": audio::output_token(&output.id),
                    "name": output.name,
                    "active": output.is_default,
                }))
                .collect::<Vec<_>>());
        }
    }
    if shared.config.feature_enabled("system_stats") {
        telemetry::merge(
            &mut state,
            telemetry::sample(shared.telemetry.clone()).await,
        );
    }
    let extension_snapshots = shared.extension_snapshots.read().unwrap().clone();
    let config = shared.config.document();
    let mut extension_panels = Vec::new();
    let mut extension_buttons = Vec::new();
    if let Some(pages) = config["pages"].as_array() {
        for page in pages {
            let page_id = page["id"].as_str().unwrap_or("");
            if let Some(reference) = page["dashboard"]
                .as_str()
                .and_then(|value| value.strip_prefix("ext:"))
            {
                if let Some((id, name)) = reference.split_once('/') {
                    let panel = extension_snapshots[id]["dashboards"][name].clone();
                    let panel = if panel.is_object() {
                        panel
                    } else {
                        json!({"title":{"en":"Extension unavailable","fr":"Extension indisponible"},"status":"warning","cards":[]})
                    };
                    let mut panel = panel;
                    panel["page"] = json!(page_id);
                    extension_panels.push(panel);
                }
            }
            if let Some(buttons) = page["buttons"].as_array() {
                for button in buttons {
                    if let Some(reference) = button["action"]["type"]
                        .as_str()
                        .and_then(|value| value.strip_prefix("ext:"))
                    {
                        if let Some((id, name)) = reference.split_once('/') {
                            let ready = extension_snapshots.get(id).is_some();
                            let active = extension_snapshots[id]["states"][name]
                                .as_bool()
                                .unwrap_or(false);
                            extension_buttons.push(json!({"page":page_id,"id":button["id"],"available":ready,"active":active}));
                        }
                    }
                }
            }
        }
    }
    state["extension_panels"] = json!(extension_panels);
    state["extension_buttons"] = json!(extension_buttons);
    *shared.latest_state.write().unwrap() = state.clone();
    state
}

async fn write_art_if_changed(
    stream: &mut TcpStream,
    shared: &Shared,
    state: &Value,
    last_token: &mut u32,
) -> Result<(), String> {
    let token = state["media"]["art"].as_u64().unwrap_or(0) as u32;
    if token == 0 {
        *last_token = 0;
        return Ok(());
    }
    if token != *last_token {
        let frame = { shared.artwork.lock().unwrap().frame_for_token(token) };
        if let Some(frame) = frame {
            protocol::write_binary(stream, &frame).await?;
            *last_token = token;
        }
    }
    Ok(())
}

async fn perform_value(shared: &Shared, message: &Value) -> Result<&'static str, String> {
    let value = message
        .get("value")
        .and_then(Value::as_u64)
        .ok_or("Invalid value")?;
    match message.get("target").and_then(Value::as_str) {
        Some("media_position") if shared.config.feature_enabled("media") => {
            let state = shared.latest_state.read().unwrap().clone();
            let duration = state["media"]["duration"]
                .as_u64()
                .ok_or("Unknown track duration")?;
            if value > duration || duration > 3600 || state["media"]["seekable"] != true {
                return Err("Playback position is unavailable".into());
            }
            system::seek_media(value).await
        }
        Some("volume") if value <= 100 => system::set_volume(value as u8).await,
        Some("app_volume") if value <= 100 && shared.config.feature_enabled("media") => {
            system::set_app_volume(value as u8).await
        }
        Some("volume" | "app_volume") if value > 100 => {
            Err("Volume must be between 0 and 100".into())
        }
        Some("app_volume") => Err("Media controls are disabled".into()),
        _ => Err("Unknown value target".into()),
    }
}

fn action_result(id: u64, ok: bool, message: &str) -> Value {
    json!({"type":"action.result","id":id,"ok":ok,"message":message})
}

fn platform_name() -> &'static str {
    #[cfg(target_os = "macos")]
    {
        "macos"
    }
    #[cfg(target_os = "windows")]
    {
        "windows"
    }
    #[cfg(target_os = "linux")]
    {
        "linux"
    }
}

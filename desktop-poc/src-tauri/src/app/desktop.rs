use crate::app::state::Shared;
use serde_json::{json, Value};

const CATALOG: &str = include_str!("../../../catalog.json");

fn platform() -> &'static str {
    #[cfg(target_os = "macos")]
    {
        "darwin"
    }
    #[cfg(target_os = "windows")]
    {
        "win32"
    }
    #[cfg(target_os = "linux")]
    {
        "linux"
    }
}

pub(crate) fn address_hints(port: u16) -> Vec<String> {
    let mut interfaces = if_addrs::get_if_addrs().unwrap_or_default();
    interfaces.retain(|interface| match &interface.addr {
        if_addrs::IfAddr::V4(address) => !address.ip.is_loopback() && !address.ip.is_link_local(),
        if_addrs::IfAddr::V6(_) => false,
    });
    interfaces.sort_by_key(|interface| {
        if interface.name == "en0"
            || interface.name.starts_with("wlan")
            || interface.name.starts_with("Wi-Fi")
        {
            0
        } else if interface.name.starts_with("en") || interface.name.starts_with("eth") {
            1
        } else {
            2
        }
    });
    interfaces
        .into_iter()
        .take(6)
        .map(|interface| format!("{}:{port}", interface.ip()))
        .collect()
}

fn supported_action(kind: &str) -> bool {
    #[cfg(target_os = "macos")]
    {
        matches!(
            kind,
            "app.launch"
                | "app.quit"
                | "audio_output.cycle"
                | "audio_output.set"
                | "app_volume.up"
                | "app_volume.down"
                | "app_volume.set"
                | "hotkey"
                | "media.next"
                | "media.play_pause"
                | "media.previous"
                | "mic.mute_toggle"
                | "mic.mute"
                | "mic.unmute"
                | "path.open"
                | "url.open"
                | "window.focus"
                | "system.lock"
                | "volume.down"
                | "volume.mute_toggle"
                | "volume.up"
                | "volume.set"
                | "obs.scene.set"
                | "obs.stream.toggle"
                | "obs.record.toggle"
                | "obs.source.toggle"
                | "modal.volumes"
                | "settings.open"
                | "frame.toggle"
                | "noop"
        )
    }
    #[cfg(target_os = "windows")]
    {
        matches!(
            kind,
            "app.launch"
                | "app.quit"
                | "app_volume.up"
                | "app_volume.down"
                | "app_volume.set"
                | "hotkey"
                | "media.next"
                | "media.play_pause"
                | "media.previous"
                | "mic.mute_toggle"
                | "mic.mute"
                | "mic.unmute"
                | "window.focus"
                | "path.open"
                | "url.open"
                | "system.lock"
                | "volume.down"
                | "volume.mute_toggle"
                | "volume.up"
                | "volume.set"
                | "modal.volumes"
                | "settings.open"
                | "frame.toggle"
                | "noop"
        )
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        matches!(
            kind,
            "modal.volumes" | "settings.open" | "frame.toggle" | "noop"
        )
    }
}

pub fn catalog(shared: &Shared) -> Result<Value, String> {
    let mut catalog: Value = serde_json::from_str(CATALOG).map_err(|error| error.to_string())?;
    let config = shared.config.document();
    let os = platform();
    let obs = config["integrations"]["obs"]["enabled"].as_bool() == Some(true);
    let notifications_available = shared.notifications.lock().unwrap().available();
    let mut capabilities = json!({
        "volume":cfg!(any(target_os = "macos", target_os = "windows")), "mute":cfg!(any(target_os = "macos", target_os = "windows")),
        "mic":cfg!(any(target_os = "macos", target_os = "windows")), "audio_output":cfg!(any(target_os = "macos", target_os = "windows")),
        "media":cfg!(any(target_os = "macos", target_os = "windows")), "app_volume":cfg!(any(target_os = "macos", target_os = "windows")),
        "apps":cfg!(any(target_os = "macos", target_os = "windows")), "windows":cfg!(any(target_os = "macos", target_os = "windows")),
        "hotkey":cfg!(any(target_os = "macos", target_os = "windows")), "open_url":cfg!(any(target_os = "macos", target_os = "windows")),
        "open_path":cfg!(any(target_os = "macos", target_os = "windows")), "lock":cfg!(any(target_os = "macos", target_os = "windows")),
        "notifications":notifications_available, "media_artwork":cfg!(any(target_os = "macos", target_os = "windows")),
        "lyrics_online":cfg!(any(target_os = "macos", target_os = "windows")),
        "system_stats":true, "obs":obs
    });
    for (feature, capability) in [
        ("audio_output", "audio_output"),
        ("media", "media"),
        ("windows", "windows"),
        ("system_stats", "system_stats"),
    ] {
        if !shared.config.feature_enabled(feature) {
            capabilities[capability] = json!(false);
        }
    }
    if !shared.config.feature_enabled("media") {
        capabilities["app_volume"] = json!(false);
    }
    catalog["capabilities"] = capabilities.clone();
    let extension_catalog = shared.extension_catalog.read().unwrap().clone();
    if let Some(actions) = catalog["actions"].as_array_mut() {
        for action in actions {
            let kind = action["kind"].as_str().unwrap_or("");
            let needed = action["capability"].as_str();
            let enabled = needed
                .map(|name| capabilities[name].as_bool().unwrap_or(false))
                .unwrap_or(true);
            action["supported"] = json!(supported_action(kind) && enabled);
        }
    }
    if let Some(features) = catalog["features"].as_array_mut() {
        for feature in features {
            let name = feature["key"].as_str().unwrap_or("").to_owned();
            if name == "media" && cfg!(target_os = "windows") {
                feature["description"]["fr"] = json!("Lit et contrôle la session multimédia Windows active ; les informations disponibles dépendent du lecteur.");
                feature["description"]["en"] = json!("Reads and controls the active Windows media session; available details depend on the player.");
            }
            if name == "audio_output" && cfg!(target_os = "windows") {
                feature["description"]["fr"] = json!("Consultez les sorties audio et choisissez la sortie par défaut dans les paramètres Son de Windows.");
                feature["description"]["en"] = json!(
                    "View audio outputs and choose the default output in Windows Sound settings."
                );
            }
            if name == "app_volume" && cfg!(target_os = "windows") {
                feature["description"]["fr"] =
                    json!("Ajuste les sessions audio WASAPI du lecteur multimédia actif.");
                feature["description"]["en"] =
                    json!("Adjusts WASAPI audio sessions for the active media player.");
            }
            let available_os = name == "system_stats"
                || feature["platforms"].as_array().is_some_and(|platforms| {
                    platforms.iter().any(|item| item.as_str() == Some(os))
                });
            let available_capability = match name.as_str() {
                "notifications" => notifications_available,
                "audio_output" | "app_volume" => {
                    cfg!(any(target_os = "macos", target_os = "windows"))
                }
                "media_artwork" => cfg!(any(target_os = "macos", target_os = "windows")),
                "lyrics_online" => cfg!(any(target_os = "macos", target_os = "windows")),
                "system_stats" => true,
                "media" | "windows" => cfg!(any(target_os = "macos", target_os = "windows")),
                _ => cfg!(target_os = "macos"),
            };
            feature["enabled"] = json!(shared.config.feature_enabled(&name));
            feature["available"] = json!(available_os && available_capability);
        }
    }
    if let Some(dashboards) = catalog["dashboards"].as_array_mut() {
        for dashboard in dashboards {
            if let Some(needed) = dashboard["capability"].as_str().map(str::to_owned) {
                dashboard["supported"] =
                    json!(capabilities[needed.as_str()].as_bool().unwrap_or(false));
            }
        }
    }
    for (field, extension_field) in [
        ("actions", "actions"),
        ("sources", "sources"),
        ("dashboards", "dashboards"),
    ] {
        if let (Some(target), Some(extra)) = (
            catalog[field].as_array_mut(),
            extension_catalog[extension_field].as_array(),
        ) {
            target.extend(extra.iter().cloned());
        }
    }
    catalog["extension_sources"] = extension_catalog["sources"].clone();
    Ok(catalog)
}

pub fn state(shared: &Shared) -> Result<Value, String> {
    let status = shared.snapshot();
    let config = shared.config.document();
    let catalog = catalog(shared)?;
    let mut snapshot = shared.latest_state.read().unwrap().clone();
    snapshot["lyrics"] = shared.latest_lyrics.read().unwrap().clone();
    let extension_snapshots = shared.extension_snapshots.read().unwrap();
    let mut extension_previews = serde_json::Map::new();
    let mut extension_sources = serde_json::Map::new();
    if let Some(packages) = extension_snapshots.as_object() {
        for (id, data) in packages {
            if let Some(panels) = data["dashboards"].as_object() {
                for (name, panel) in panels {
                    extension_previews.insert(format!("ext:{id}/{name}"), panel.clone());
                }
            }
            if let Some(sources) = data["sources"].as_object() {
                for (name, entries) in sources {
                    let entries = entries
                        .as_array()
                        .map(|items| {
                            items
                                .iter()
                                .map(|item| {
                                    let mut item = item.clone();
                                    if let Some(object) = item.as_object_mut() {
                                        object.remove("action");
                                    }
                                    item
                                })
                                .collect::<Vec<_>>()
                        })
                        .unwrap_or_default();
                    extension_sources
                        .insert(format!("ext:{id}/{name}"), serde_json::json!(entries));
                }
            }
        }
    }
    snapshot["extension_previews"] = Value::Object(extension_previews);
    snapshot["extension_sources"] = Value::Object(extension_sources);
    let windows = shared.windows.read().unwrap();
    snapshot["apps"] = json!(windows.iter().map(|window| &window.app).collect::<Vec<_>>());
    snapshot["active_app"] = json!(windows
        .first()
        .map(|window| window.app.as_str())
        .unwrap_or(""));
    let features = config["features"].clone();
    Ok(json!({
        "version":"0.1.0", "config_revision":status.config_revision,
        "platform":platform(), "listen":format!("0.0.0.0:{}", status.tcp_port),
        "hints":address_hints(status.tcp_port),
        "token_set":false,
        "pairing":{"required":true,"code":status.pairing_code,"expires_in":0},
        "discovery_port":status.discovery_port,
        "clients":shared.clients(), "paired_devices":shared.paired_devices(),
        "capabilities":catalog["capabilities"], "features":features,
        "notifications":shared.notifications.lock().unwrap().status(),
        "snapshot":snapshot,
        "logs":[status.last_event], "events":[], "counters":{},
        "paused":false, "pause_remaining":null
    }))
}

pub fn apps(shared: &Shared) -> Value {
    let windows = shared.windows.read().unwrap();
    let mut names: Vec<String> = windows.iter().map(|window| window.app.clone()).collect();
    names.sort();
    names.dedup();
    json!({"apps":names})
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bundled_catalog_has_full_editor_contract() {
        let value: Value = serde_json::from_str(CATALOG).unwrap();
        assert!(value["actions"].as_array().unwrap().len() >= 30);
        assert!(value["icons"].as_array().unwrap().len() > 10);
        assert!(value["limits"]["buttons_per_page"].is_number());
    }
}

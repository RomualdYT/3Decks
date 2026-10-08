use serde_json::json;
use serde_json::Value;
#[cfg(any(target_os = "macos", target_os = "windows"))]
use std::sync::Mutex;

#[cfg(any(target_os = "macos", target_os = "windows"))]
static PREVIOUS_INPUT_VOLUME: Mutex<Option<u8>> = Mutex::new(None);

pub async fn change_volume(direction: i8, step: u8) -> Result<&'static str, String> {
    #[cfg(any(target_os = "macos", target_os = "windows"))]
    {
        let delta = if direction > 0 {
            step as i16
        } else {
            -(step as i16)
        };
        let (current, _) = super::audio::output_state().await?;
        super::audio::set_output_volume((i16::from(current) + delta).clamp(0, 100) as u8).await?;
        return Ok("Volume changed");
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = (direction, step);
        Err("Volume action is not implemented on this platform".into())
    }
}

pub async fn perform(action: &Value, volume_step: u8) -> Result<&'static str, String> {
    let kind = action
        .as_str()
        .or_else(|| action.get("type").and_then(Value::as_str))
        .ok_or("Action type missing")?;
    match kind {
        "noop" => Ok("No action"),
        "volume.up" => change_volume(1, action_step(action, volume_step)?).await,
        "volume.down" => change_volume(-1, action_step(action, volume_step)?).await,
        "volume.set" => set_volume(action_value(action, "value")?).await,
        "volume.mute_toggle" => toggle_mute().await,
        "mic.mute_toggle" => toggle_mic().await,
        "mic.mute" => set_mic_muted(true).await,
        "mic.unmute" => set_mic_muted(false).await,
        "app_volume.up" => change_app_volume(1, action_step(action, volume_step)?).await,
        "app_volume.down" => change_app_volume(-1, action_step(action, volume_step)?).await,
        "app_volume.set" => set_app_volume(action_value(action, "value")?).await,
        "media.play_pause" => media_command("playpause").await,
        "media.next" => media_command("next track").await,
        "media.previous" => media_command("previous track").await,
        "hotkey" => hotkey(action["keys"].as_str().ok_or("Hotkey missing keys")?).await,
        "app.launch" => launch_app(action["target"].as_str().ok_or("App target missing")?).await,
        "app.quit" => quit_app(action["target"].as_str().ok_or("App target missing")?).await,
        "url.open" => open_url(action["url"].as_str().ok_or("URL missing")?).await,
        "path.open" => open_path(action["path"].as_str().ok_or("Path missing")?).await,
        "system.lock" => lock_session().await,
        _ => Err(format!("Action {kind} is not ported yet")),
    }
}

fn action_step(action: &Value, default: u8) -> Result<u8, String> {
    let Some(value) = action.get("step") else {
        return Ok(default);
    };
    let step = value.as_u64().ok_or("Volume step must be an integer")?;
    if !(1..=50).contains(&step) {
        return Err("Volume step must be between 1 and 50".into());
    }
    Ok(step as u8)
}

fn action_value(action: &Value, field: &str) -> Result<u8, String> {
    let value = action[field]
        .as_u64()
        .ok_or_else(|| format!("{field} must be an integer"))?;
    if value > 100 {
        return Err(format!("{field} must be between 0 and 100"));
    }
    Ok(value as u8)
}

async fn change_app_volume(direction: i8, step: u8) -> Result<&'static str, String> {
    #[cfg(target_os = "macos")]
    {
        let current = i16::from(super::macos::media::volume().await?);
        let next = (current + i16::from(direction) * i16::from(step)).clamp(0, 100);
        set_app_volume(next as u8).await
    }
    #[cfg(target_os = "windows")]
    {
        super::windows::audio_sessions::change_active_media_volume(direction, step).await?;
        Ok("Player volume changed")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = (direction, step);
        Err("Player volume is not implemented on this platform yet".into())
    }
}

async fn set_mic_muted(muted: bool) -> Result<&'static str, String> {
    #[cfg(any(target_os = "macos", target_os = "windows"))]
    {
        let current = super::audio::input_volume().await?;
        if muted && current > 0 {
            *PREVIOUS_INPUT_VOLUME.lock().unwrap() = Some(current);
            super::audio::set_input_volume(0).await?;
        } else if !muted && current == 0 {
            let restore = PREVIOUS_INPUT_VOLUME
                .lock()
                .unwrap()
                .take()
                .unwrap_or(50)
                .max(1);
            super::audio::set_input_volume(restore).await?;
        }
        Ok("Microphone mute changed")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = muted;
        Err("Microphone mute is not implemented on this platform yet".into())
    }
}

async fn open_url(input: &str) -> Result<&'static str, String> {
    let parsed = normalized_url(input)?;
    #[cfg(target_os = "macos")]
    {
        super::macos::workspace::open_web_url(parsed.as_str()).await?;
        Ok("URL opened")
    }
    #[cfg(target_os = "windows")]
    {
        super::windows::shell::open(parsed.as_str()).await?;
        Ok("URL opened")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = parsed;
        Err("URL opening is not implemented on this platform yet".into())
    }
}

fn normalized_url(input: &str) -> Result<url::Url, String> {
    let input = input.trim();
    if input.is_empty() || input.len() > 2048 || input.chars().any(|value| value.is_control()) {
        return Err("Invalid URL".into());
    }
    let value = if input.contains("://") {
        input.to_owned()
    } else {
        format!("https://{input}")
    };
    let parsed = url::Url::parse(&value).map_err(|_| "Invalid URL")?;
    if !matches!(parsed.scheme(), "http" | "https")
        || parsed.host_str().is_none()
        || parsed.username() != ""
        || parsed.password().is_some()
    {
        return Err("Only HTTP(S) URLs without credentials are supported".into());
    }
    Ok(parsed)
}

async fn quit_app(target: &str) -> Result<&'static str, String> {
    if target.is_empty() || target.len() > 256 {
        return Err("Invalid app target".into());
    }
    #[cfg(target_os = "macos")]
    {
        super::macos::workspace::quit_app(target).await?;
        Ok("Application quit")
    }
    #[cfg(target_os = "windows")]
    {
        super::windows::process::quit_app(target).await?;
        Ok("Application close requested")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        Err("Application quit is not implemented on this platform yet".into())
    }
}

async fn lock_session() -> Result<&'static str, String> {
    #[cfg(target_os = "macos")]
    {
        super::macos::keyboard::send("ctrl+cmd+q").await?;
        Ok("Session locked")
    }
    #[cfg(target_os = "windows")]
    {
        super::windows::shell::lock_session().await?;
        Ok("Session locked")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        Err("Session locking is not implemented on this platform yet".into())
    }
}

pub async fn set_volume(value: u8) -> Result<&'static str, String> {
    if value > 100 {
        return Err("Volume must be between 0 and 100".into());
    }
    #[cfg(any(target_os = "macos", target_os = "windows"))]
    {
        super::audio::set_output_volume(value).await?;
        Ok("Volume changed")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = value;
        Err("Volume setting is not implemented on this platform yet".into())
    }
}

pub async fn set_app_volume(value: u8) -> Result<&'static str, String> {
    if value > 100 {
        return Err("App volume must be between 0 and 100".into());
    }
    #[cfg(target_os = "macos")]
    {
        super::macos::media::set_volume(value).await?;
        Ok("Player volume changed")
    }
    #[cfg(target_os = "windows")]
    {
        super::windows::audio_sessions::set_active_media_volume(value).await?;
        Ok("Player volume changed")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = value;
        Err("Player volume is not implemented on this platform yet".into())
    }
}

pub async fn seek_media(seconds: u64) -> Result<&'static str, String> {
    #[cfg(target_os = "macos")]
    {
        super::macos::media::seek(seconds as f64).await?;
        Ok("Playback position changed")
    }
    #[cfg(target_os = "windows")]
    {
        super::windows::media::seek(seconds).await?;
        Ok("Playback position changed")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = seconds;
        Err("Seeking is not available for this media player".into())
    }
}

pub struct SystemSnapshot {
    pub state: Value,
    pub artwork_key: Option<String>,
    pub artwork_bytes: Option<std::sync::Arc<[u8]>>,
}

pub async fn state_snapshot(include_media: bool, include_artwork: bool) -> SystemSnapshot {
    #[cfg(any(target_os = "macos", target_os = "windows"))]
    {
        #[cfg(target_os = "macos")]
        use super::macos::media as native_media;
        #[cfg(target_os = "windows")]
        use super::windows::media as native_media;

        let (output, input, media) = tokio::join!(
            super::audio::output_state(),
            super::audio::input_volume(),
            async {
                if include_media {
                    native_media::snapshot(include_artwork).await
                } else {
                    Ok(None)
                }
            }
        );
        let mut state = json!({"type":"state.update","volume":null,"muted":null,"mic_muted":null,"media":null,"app_volume":null});
        if let Ok((volume, muted)) = output {
            state["volume"] = json!(volume);
            state["muted"] = json!(muted);
        }
        if let Ok(input) = input {
            state["mic_muted"] = json!(input == 0);
        }
        let mut artwork_key = None;
        let mut artwork_bytes = None;
        if let Ok(Some(snapshot)) = media {
            state["app_volume"] = json!(snapshot.app_volume);
            state["media"] = snapshot.media;
            artwork_key = snapshot.artwork_key;
            artwork_bytes = snapshot.artwork;
        }
        return SystemSnapshot {
            state,
            artwork_key,
            artwork_bytes,
        };
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = (include_media, include_artwork);
        SystemSnapshot {
            state: json!({"type":"state.update","volume":null,"muted":null,"mic_muted":null,"media":null,"app_volume":null}),
            artwork_key: None,
            artwork_bytes: None,
        }
    }
}

async fn media_command(command: &str) -> Result<&'static str, String> {
    #[cfg(target_os = "macos")]
    {
        super::macos::media::command(command).await?;
        Ok("Media command sent")
    }
    #[cfg(target_os = "windows")]
    {
        super::windows::media::command(command).await?;
        Ok("Media command sent")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = command;
        Err("Media control is not implemented on this platform yet".into())
    }
}

async fn hotkey(keys: &str) -> Result<&'static str, String> {
    #[cfg(target_os = "macos")]
    {
        super::macos::keyboard::send(keys).await?;
        Ok("Shortcut sent")
    }
    #[cfg(target_os = "windows")]
    {
        super::windows::keyboard::hotkey(keys).await?;
        Ok("Shortcut sent")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = keys;
        Err("Hotkeys are not implemented on this platform yet".into())
    }
}

async fn toggle_mute() -> Result<&'static str, String> {
    #[cfg(any(target_os = "macos", target_os = "windows"))]
    {
        let (_, muted) = super::audio::output_state().await?;
        super::audio::set_output_muted(!muted).await?;
        Ok("Mute changed")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        Err("Mute action is not implemented on this platform yet".into())
    }
}

async fn toggle_mic() -> Result<&'static str, String> {
    #[cfg(any(target_os = "macos", target_os = "windows"))]
    {
        let volume = super::audio::input_volume().await?;
        if volume == 0 {
            let previous = *PREVIOUS_INPUT_VOLUME.lock().unwrap();
            let restore = previous.unwrap_or(50).max(1);
            super::audio::set_input_volume(restore).await?;
            *PREVIOUS_INPUT_VOLUME.lock().unwrap() = None;
        } else {
            super::audio::set_input_volume(0).await?;
            *PREVIOUS_INPUT_VOLUME.lock().unwrap() = Some(volume);
        }
        Ok("Microphone mute changed")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        Err("Microphone mute is not implemented on this platform yet".into())
    }
}

async fn launch_app(target: &str) -> Result<&'static str, String> {
    if target.is_empty() || target.len() > 2048 {
        return Err("Invalid app target".into());
    }
    #[cfg(target_os = "macos")]
    {
        super::macos::workspace::launch_app(target).await?;
        Ok("Application launched")
    }
    #[cfg(target_os = "windows")]
    {
        let target = super::windows::applications::launch_target(target).await;
        super::windows::shell::open(&target).await?;
        Ok("Application launched")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        Err("Application launch is not implemented on this platform yet".into())
    }
}

async fn open_path(path: &str) -> Result<&'static str, String> {
    if path.is_empty() || path.len() > 4096 {
        return Err("Invalid path".into());
    }
    #[cfg(target_os = "macos")]
    {
        let expanded = if path == "~" {
            std::env::var("HOME").map_err(|e| e.to_string())?
        } else if let Some(suffix) = path.strip_prefix("~/") {
            format!(
                "{}/{suffix}",
                std::env::var("HOME").map_err(|e| e.to_string())?
            )
        } else {
            path.to_string()
        };
        super::macos::workspace::open_file(&expanded).await?;
        Ok("Path opened")
    }
    #[cfg(target_os = "windows")]
    {
        let expanded = if path == "~" {
            std::env::var("USERPROFILE").map_err(|error| error.to_string())?
        } else if let Some(suffix) = path.strip_prefix("~/").or_else(|| path.strip_prefix("~\\")) {
            format!(
                "{}\\{suffix}",
                std::env::var("USERPROFILE").map_err(|error| error.to_string())?
            )
        } else {
            path.to_owned()
        };
        super::windows::shell::open(&expanded).await?;
        Ok("Path opened")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        Err("Path opening is not implemented on this platform yet".into())
    }
}

#[cfg(all(test, target_os = "macos"))]
mod tests {
    use super::{action_step, normalized_url};
    use serde_json::json;

    #[test]
    fn rejects_unsafe_urls_and_volume_steps() {
        assert_eq!(
            normalized_url("example.com").unwrap().as_str(),
            "https://example.com/"
        );
        assert!(normalized_url("file:///etc/passwd").is_err());
        assert!(normalized_url("https://user:pass@example.com").is_err());
        assert!(normalized_url("https://example.com\nother").is_err());
        assert_eq!(action_step(&json!({"step":12}), 5).unwrap(), 12);
        assert!(action_step(&json!({"step":51}), 5).is_err());
    }
}

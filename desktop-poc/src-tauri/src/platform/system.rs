use serde_json::json;
use serde_json::Value;
#[cfg(any(target_os = "macos", target_os = "windows"))]
use std::sync::Mutex;
#[cfg(target_os = "macos")]
use std::time::Duration;
#[cfg(target_os = "macos")]
use tokio::process::Command;

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
        let player = active_player()
            .await
            .ok_or("No supported media player is running")?;
        let current = script_output(&format!(
            "tell application \"{player}\" to get sound volume"
        ))
        .await?
        .parse::<i16>()
        .map_err(|_| "Unable to read player volume")?;
        let next = (current + i16::from(direction) * i16::from(step)).clamp(0, 100);
        set_app_volume(next as u8).await
    }
    #[cfg(not(target_os = "macos"))]
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
        super::win32::shell::open(parsed.as_str()).await?;
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
        super::win32::process::quit_app(target).await?;
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
        super::win32::shell::lock_session().await?;
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
        let player = active_player()
            .await
            .ok_or("No supported media player is running")?;
        run_osascript(&format!(
            "tell application \"{player}\" to set sound volume to {value}"
        ))
        .await?;
        Ok("Player volume changed")
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = value;
        Err("Player volume is not implemented on this platform yet".into())
    }
}

pub async fn state_snapshot(include_media: bool, include_artwork: bool) -> Value {
    #[cfg(target_os = "macos")]
    {
        let mut state = json!({"type":"state.update","volume":null,"muted":null,"mic_muted":null,"media":null,"app_volume":null});
        if let Ok((volume, muted)) = super::audio::output_state().await {
            state["volume"] = json!(volume);
            state["muted"] = json!(muted);
        }
        if let Ok(input) = super::audio::input_volume().await {
            state["mic_muted"] = json!(input == 0);
        }
        if let Some(player) = if include_media {
            active_player().await
        } else {
            None
        } {
            let art_script = if !include_artwork {
                ""
            } else if player == "Spotify" {
                "try\nset deckArt to artwork url of deckTrack\nend try"
            } else {
                "try\nset deckArtwork to artwork 1 of deckTrack\nset deckArtworkId to persistent ID of deckTrack\nset deckArtPath to (POSIX path of (path to temporary items)) & \"3decks-music-\" & deckArtworkId & \".art\"\nset deckArtFile to open for access POSIX file deckArtPath with write permission\nset eof deckArtFile to 0\nwrite (raw data of deckArtwork) to deckArtFile starting at 0\nclose access deckArtFile\nset deckArt to \"file://\" & deckArtPath\non error\ntry\nclose access deckArtFile\nend try\nend try"
            };
            let script = format!(
                r#"tell application "{player}"
set deckState to player state as text
set deckTitle to ""
set deckArtist to ""
set deckAlbum to ""
set deckArt to ""
set deckPos to ""
set deckDur to ""
try
set deckTrack to current track
set deckTitle to name of deckTrack
set deckArtist to artist of deckTrack
set deckAlbum to album of deckTrack
set deckDur to duration of deckTrack as text
{art_script}
end try
try
set deckPos to player position as text
end try
return deckState & "\n" & deckTitle & "\n" & deckArtist & "\n" & deckAlbum & "\n" & deckArt & "\n" & deckPos & "\n" & deckDur & "\n" & (sound volume as text)
end tell"#
            );
            if let Ok(text) = script_output(&script).await {
                let fields: Vec<_> = text.splitn(8, '\n').collect();
                if fields.len() == 8 {
                    if let Ok(volume) = fields[7].parse::<u8>() {
                        state["app_volume"] = json!(volume.min(100));
                    }
                }
                if fields.len() == 8 && !fields[1].is_empty() {
                    let mut media = json!({"app":if player == "Music" {"Apple Music"} else {player}, "playing":fields[0] == "playing", "title":fields[1], "artist":fields[2], "album":fields[3], "art_url":fields[4]});
                    let duration = fields[6]
                        .replace(',', ".")
                        .parse::<f64>()
                        .ok()
                        .map(|value| {
                            if value > 10_000.0 {
                                value / 1000.0
                            } else {
                                value
                            }
                        });
                    if let Some(duration) =
                        duration.filter(|value| value.is_finite() && *value > 0.0)
                    {
                        media["duration"] = json!(duration as u64);
                        if let Ok(position) = fields[5].replace(',', ".").parse::<f64>() {
                            if position.is_finite() {
                                media["position"] = json!(position.clamp(0.0, duration) as u64);
                            }
                        }
                    }
                    state["media"] = media;
                }
            }
        }
        return state;
    }
    #[cfg(target_os = "windows")]
    {
        let _ = (include_media, include_artwork);
        let mut state = json!({"type":"state.update","volume":null,"muted":null,"mic_muted":null,"media":null,"app_volume":null});
        if let Ok((volume, muted)) = super::audio::output_state().await {
            state["volume"] = json!(volume);
            state["muted"] = json!(muted);
        }
        if let Ok(input) = super::audio::input_volume().await {
            state["mic_muted"] = json!(input == 0);
        }
        state
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = (include_media, include_artwork);
        json!({"type":"state.update","volume":null,"muted":null,"mic_muted":null,"media":null,"app_volume":null})
    }
}

#[cfg(target_os = "macos")]
async fn run_osascript(script: &str) -> Result<(), String> {
    script_output(script).await.map(|_| ())
}

#[cfg(target_os = "macos")]
async fn script_output(script: &str) -> Result<String, String> {
    let output = tokio::time::timeout(
        Duration::from_secs(3),
        Command::new("/usr/bin/osascript")
            .kill_on_drop(true)
            .arg("-e")
            .arg(script)
            .output(),
    )
    .await
    .map_err(|_| "AppleScript timed out".to_string())?
    .map_err(|e| e.to_string())?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).trim().to_string())
    }
}

#[cfg(target_os = "macos")]
async fn active_player() -> Option<&'static str> {
    super::macos::media::active_player().await
}

async fn media_command(command: &str) -> Result<&'static str, String> {
    #[cfg(target_os = "macos")]
    {
        super::macos::media::command(command).await?;
        Ok("Media command sent")
    }
    #[cfg(target_os = "windows")]
    {
        super::win32::keyboard::media(command)?;
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
        super::win32::keyboard::hotkey(keys)?;
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
    if target.is_empty() || target.len() > 256 {
        return Err("Invalid app target".into());
    }
    #[cfg(target_os = "macos")]
    {
        super::macos::workspace::launch_app(target).await?;
        Ok("Application launched")
    }
    #[cfg(target_os = "windows")]
    {
        super::win32::shell::open(target).await?;
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
        super::win32::shell::open(&expanded).await?;
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

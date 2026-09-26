use serde::Serialize;
use sha2::{Digest, Sha256};

#[derive(Clone, Debug, Serialize)]
pub struct Output {
    pub id: String,
    pub name: String,
    pub is_default: bool,
}

/// Identifiant court transmis à la console. Le véritable identifiant système
/// reste sur l'ordinateur et est retrouvé lors de la sélection.
pub fn output_token(id: &str) -> String {
    let digest = Sha256::digest(id.as_bytes());
    hex::encode(&digest[..16])
}

pub async fn select_token(token: &str) -> Result<String, String> {
    #[cfg(not(target_os = "macos"))]
    {
        let _ = token;
        return Err("Audio output selection is not available on this platform".into());
    }
    #[cfg(target_os = "macos")]
    {
        if token.len() != 32 || !token.bytes().all(|byte| byte.is_ascii_hexdigit()) {
            return Err("Invalid audio output identifier".into());
        }
        let token = token.to_owned();
        tokio::task::spawn_blocking(move || {
            let device = enumerate()?
                .into_iter()
                .find(|device| output_token(&device.id) == token)
                .ok_or("Audio output is no longer available")?;
            set_default(&device.id)?;
            Ok(device.name)
        })
        .await
        .map_err(|error| error.to_string())?
    }
}

pub async fn outputs() -> Result<Vec<Output>, String> {
    tokio::task::spawn_blocking(enumerate)
        .await
        .map_err(|error| error.to_string())?
}

pub async fn cycle() -> Result<String, String> {
    tokio::task::spawn_blocking(|| {
        let devices = enumerate()?;
        if devices.len() < 2 {
            return Err("Only one audio output is available".into());
        }
        let current = devices.iter().position(|device| device.is_default);
        let next = devices
            .get(current.map_or(0, |index| (index + 1) % devices.len()))
            .unwrap();
        set_default(&next.id)?;
        Ok(next.name.clone())
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn select(name: &str) -> Result<String, String> {
    let wanted = name.trim().to_owned();
    if wanted.is_empty() {
        return Err("Audio output name is required".into());
    }
    tokio::task::spawn_blocking(move || {
        let device = enumerate()?
            .into_iter()
            .find(|device| device.id == wanted || device.name.eq_ignore_ascii_case(&wanted))
            .ok_or_else(|| format!("Audio output not found: {wanted}"))?;
        set_default(&device.id)?;
        Ok(device.name)
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn open_settings() -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        return super::windows::shell::open("ms-settings:sound").await;
    }
    #[cfg(target_os = "macos")]
    {
        Err("Open Sound settings from System Settings on macOS".into())
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        Err("Audio output settings are not available on this platform".into())
    }
}

#[cfg(any(target_os = "macos", target_os = "windows"))]
pub async fn output_state() -> Result<(u8, bool), String> {
    tokio::task::spawn_blocking(native_audio::output_state)
        .await
        .map_err(|e| e.to_string())?
}

#[cfg(any(target_os = "macos", target_os = "windows"))]
pub async fn input_volume() -> Result<u8, String> {
    tokio::task::spawn_blocking(native_audio::input_volume)
        .await
        .map_err(|e| e.to_string())?
}

#[cfg(any(target_os = "macos", target_os = "windows"))]
pub async fn set_output_volume(value: u8) -> Result<(), String> {
    tokio::task::spawn_blocking(move || native_audio::set_output_volume(value))
        .await
        .map_err(|e| e.to_string())?
}

#[cfg(any(target_os = "macos", target_os = "windows"))]
pub async fn set_output_muted(value: bool) -> Result<(), String> {
    tokio::task::spawn_blocking(move || native_audio::set_output_muted(value))
        .await
        .map_err(|e| e.to_string())?
}

#[cfg(any(target_os = "macos", target_os = "windows"))]
pub async fn set_input_volume(value: u8) -> Result<(), String> {
    tokio::task::spawn_blocking(move || native_audio::set_input_volume(value))
        .await
        .map_err(|e| e.to_string())?
}

#[cfg(target_os = "macos")]
use super::macos::audio as native_audio;
#[cfg(target_os = "windows")]
use super::windows::audio as native_audio;

#[cfg(target_os = "windows")]
fn enumerate() -> Result<Vec<Output>, String> {
    super::windows::audio::enumerate()
}

#[cfg(target_os = "linux")]
fn enumerate() -> Result<Vec<Output>, String> {
    Err("Audio output selection is not implemented on this platform yet".into())
}

#[cfg(target_os = "windows")]
fn set_default(_id: &str) -> Result<(), String> {
    Err("Windows requires choosing the default output in Sound settings".into())
}

#[cfg(target_os = "linux")]
fn set_default(_id: &str) -> Result<(), String> {
    Err("Audio output selection is not implemented on this platform yet".into())
}

#[cfg(target_os = "macos")]
use super::macos::audio::{enumerate, set_default};

#[cfg(all(test, target_os = "macos"))]
mod tests {
    use super::*;

    #[test]
    fn coreaudio_lists_and_reapplies_current_output() {
        let devices = enumerate().expect("CoreAudio should enumerate outputs");
        // Headless macOS runners may have no default output.
        let Some(current) = devices.iter().find(|device| device.is_default) else {
            return;
        };
        assert!(!current.name.is_empty());
        set_default(&current.id).expect("Current output should remain selectable");
    }
}

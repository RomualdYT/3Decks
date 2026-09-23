use serde::Serialize;

#[derive(Clone, Debug, Serialize)]
pub struct Output {
    pub name: String,
    pub is_default: bool,
    #[serde(skip)]
    pub(crate) id: u32,
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
        set_default(next.id)?;
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
            .find(|device| device.name.to_lowercase().contains(&wanted.to_lowercase()))
            .ok_or_else(|| format!("Audio output not found: {wanted}"))?;
        set_default(device.id)?;
        Ok(device.name)
    })
    .await
    .map_err(|error| error.to_string())?
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
use super::win32::audio as native_audio;

#[cfg(not(target_os = "macos"))]
fn enumerate() -> Result<Vec<Output>, String> {
    Err("Audio output selection is not implemented on this platform yet".into())
}

#[cfg(not(target_os = "macos"))]
fn set_default(_id: u32) -> Result<(), String> {
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
        set_default(current.id).expect("Current output should remain selectable");
    }
}

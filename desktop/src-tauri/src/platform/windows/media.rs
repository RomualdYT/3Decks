//! System media sessions through Windows Runtime's GSMTC API.
//!
//! WinRT work is isolated on Tokio's blocking pool because its operations are
//! synchronous at this boundary. The public surface only returns owned Rust
//! data; Windows COM objects never leak into shared application code.

use serde_json::{json, Value};
use std::sync::{Arc, Mutex};
use windows::Media::Control::{
    GlobalSystemMediaTransportControlsSession, GlobalSystemMediaTransportControlsSessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus,
};
use windows::Storage::Streams::{Buffer, DataReader, InputStreamOptions};
use windows::Win32::System::WinRT::{RoInitialize, RoUninitialize, RO_INIT_MULTITHREADED};

const MAX_ARTWORK_BYTES: u64 = 4 * 1024 * 1024;
const TICKS_PER_SECOND: i64 = 10_000_000;
const NO_ACTIVE_SESSION: &str = "No controllable media session is active";

static ARTWORK_CACHE: Mutex<Option<(String, Arc<[u8]>)>> = Mutex::new(None);

struct WinRtApartment;

impl WinRtApartment {
    fn enter() -> Result<Self, String> {
        unsafe { RoInitialize(RO_INIT_MULTITHREADED) }.map_err(|error| error.to_string())?;
        Ok(Self)
    }
}

impl Drop for WinRtApartment {
    fn drop(&mut self) {
        unsafe { RoUninitialize() };
    }
}

pub struct MediaSnapshot {
    pub media: Value,
    pub app_volume: Option<u8>,
    pub artwork_key: Option<String>,
    pub artwork: Option<Arc<[u8]>>,
}

fn source_label(app_id: &str) -> String {
    let id = app_id.to_ascii_lowercase();
    if id.contains("spotify") {
        return "Spotify".into();
    }
    if id.contains("applemusic") || id.contains("apple.music") {
        return "Apple Music".into();
    }
    if id.contains("msedge") {
        return "Microsoft Edge".into();
    }
    if id.contains("chrome") {
        return "Google Chrome".into();
    }
    if id.contains("firefox") {
        return "Firefox".into();
    }
    let label = app_id.rsplit('!').next().unwrap_or(app_id);
    let label = label.strip_suffix(".exe").unwrap_or(label);
    if label.is_empty() {
        "Media player".into()
    } else {
        label.to_owned()
    }
}

fn read_thumbnail(
    properties: &windows::Media::Control::GlobalSystemMediaTransportControlsSessionMediaProperties,
    key: &str,
) -> Result<Option<Arc<[u8]>>, String> {
    if let Some((cached_key, bytes)) = ARTWORK_CACHE.lock().unwrap().as_ref() {
        if cached_key == key {
            return Ok(Some(bytes.clone()));
        }
    }
    let Ok(reference) = properties.Thumbnail() else {
        return Ok(None);
    };
    let stream = reference
        .OpenReadAsync()
        .map_err(|error| error.to_string())?
        .join()
        .map_err(|error| error.to_string())?;
    let size = stream.Size().map_err(|error| error.to_string())?;
    if size == 0 || size > MAX_ARTWORK_BYTES {
        return Ok(None);
    }
    let size = u32::try_from(size).map_err(|error| error.to_string())?;
    let buffer = Buffer::Create(size).map_err(|error| error.to_string())?;
    let filled = stream
        .ReadAsync(&buffer, size, InputStreamOptions::None)
        .map_err(|error| error.to_string())?
        .join()
        .map_err(|error| error.to_string())?;
    let length = filled.Length().map_err(|error| error.to_string())? as usize;
    if length == 0 || length > MAX_ARTWORK_BYTES as usize {
        return Ok(None);
    }
    let reader = DataReader::FromBuffer(&filled).map_err(|error| error.to_string())?;
    let mut bytes = vec![0; length];
    reader
        .ReadBytes(&mut bytes)
        .map_err(|error| error.to_string())?;
    let _ = reader.Close();
    let bytes: Arc<[u8]> = bytes.into();
    *ARTWORK_CACHE.lock().unwrap() = Some((key.to_owned(), bytes.clone()));
    Ok(Some(bytes))
}

fn inspect_session(
    session: &GlobalSystemMediaTransportControlsSession,
    include_artwork: bool,
) -> Result<MediaSnapshot, String> {
    let properties = session
        .TryGetMediaPropertiesAsync()
        .map_err(|error| error.to_string())?
        .join()
        .map_err(|error| error.to_string())?;
    let title = properties
        .Title()
        .map_err(|error| error.to_string())?
        .to_string();
    if title.trim().is_empty() {
        return Err("The active media session has no track title".into());
    }
    let artist = properties
        .Artist()
        .map(|value| value.to_string())
        .unwrap_or_default();
    let album = properties
        .AlbumTitle()
        .map(|value| value.to_string())
        .unwrap_or_default();
    let app_id = session
        .SourceAppUserModelId()
        .map(|value| value.to_string())
        .unwrap_or_default();
    let app_volume = super::audio_sessions::volume_for_source(&app_id)
        .ok()
        .flatten();
    let playback = session
        .GetPlaybackInfo()
        .map_err(|error| error.to_string())?;
    let is_playing = playback.PlaybackStatus().is_ok_and(|state| {
        state == GlobalSystemMediaTransportControlsSessionPlaybackStatus::Playing
    });
    let timeline = session
        .GetTimelineProperties()
        .map_err(|error| error.to_string())?;
    let start = timeline
        .StartTime()
        .map(|value| value.Duration)
        .unwrap_or(0);
    let end = timeline.EndTime().map(|value| value.Duration).unwrap_or(0);
    let position = timeline
        .Position()
        .map(|value| value.Duration)
        .unwrap_or(start);
    let duration = ((end - start).max(0) / TICKS_PER_SECOND) as u64;
    let position = ((position - start).max(0) / TICKS_PER_SECOND) as u64;
    let controls = playback.Controls().map_err(|error| error.to_string())?;
    let seekable = controls.IsPlaybackPositionEnabled().unwrap_or(false);

    let mut media = json!({
        "app": source_label(&app_id),
        "playing": is_playing,
        "title": title,
        "artist": artist,
        "album": album
    });
    if duration > 0 {
        media["duration"] = json!(duration);
        media["seekable"] = json!(seekable);
        media["position"] = json!(position.min(duration));
    }
    let artwork_key = format!("{}\0{}\0{}\0{}", app_id, title, artist, album);
    let artwork = if include_artwork {
        read_thumbnail(&properties, &artwork_key).ok().flatten()
    } else {
        None
    };
    Ok(MediaSnapshot {
        media,
        app_volume,
        artwork_key: artwork.as_ref().map(|_| artwork_key),
        artwork,
    })
}

fn with_session<T>(
    operation: impl FnOnce(&GlobalSystemMediaTransportControlsSession) -> Result<T, String>,
) -> Result<T, String> {
    let _apartment = WinRtApartment::enter()?;
    let manager = GlobalSystemMediaTransportControlsSessionManager::RequestAsync()
        .map_err(|error| error.to_string())?
        .join()
        .map_err(|error| error.to_string())?;
    let session = manager
        .GetCurrentSession()
        .map_err(|_| NO_ACTIVE_SESSION.to_owned())?;
    operation(&session)
}

pub async fn snapshot(include_artwork: bool) -> Result<Option<MediaSnapshot>, String> {
    tokio::task::spawn_blocking(move || {
        match with_session(|session| inspect_session(session, include_artwork)) {
            Ok(snapshot) => Ok(Some(snapshot)),
            Err(error) if error == NO_ACTIVE_SESSION => Ok(None),
            Err(error) if error == "The active media session has no track title" => Ok(None),
            Err(error) => Err(error),
        }
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn active_source_app_id() -> Result<Option<String>, String> {
    tokio::task::spawn_blocking(|| {
        with_session(|session| {
            session
                .SourceAppUserModelId()
                .map(|value| value.to_string())
                .map_err(|error| error.to_string())
        })
    })
    .await
    .map_err(|error| error.to_string())?
    .map(Some)
    .or_else(|error| {
        if error == NO_ACTIVE_SESSION {
            Ok(None)
        } else {
            Err(error)
        }
    })
}

pub async fn command(command: &str) -> Result<(), String> {
    let command = command.to_owned();
    tokio::task::spawn_blocking(move || {
        with_session(|session| {
            let operation = match command.as_str() {
                "playpause" => session.TryTogglePlayPauseAsync(),
                "next track" => session.TrySkipNextAsync(),
                "previous track" => session.TrySkipPreviousAsync(),
                _ => return Err(format!("Unsupported media command: {command}")),
            }
            .map_err(|error| error.to_string())?;
            if operation.join().map_err(|error| error.to_string())? {
                Ok(())
            } else {
                Err("The active media session rejected the command".into())
            }
        })
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn seek(seconds: u64) -> Result<(), String> {
    tokio::task::spawn_blocking(move || {
        with_session(|session| {
            let timeline = session
                .GetTimelineProperties()
                .map_err(|error| error.to_string())?;
            let start = timeline
                .StartTime()
                .map(|value| value.Duration)
                .unwrap_or(0);
            let end = timeline.EndTime().map(|value| value.Duration).unwrap_or(0);
            let offset = i64::try_from(seconds)
                .map_err(|error| error.to_string())?
                .checked_mul(TICKS_PER_SECOND)
                .ok_or("Invalid playback position")?;
            if end > start && offset > end - start {
                return Err("Playback position is outside the active track".into());
            }
            let ticks = start
                .checked_add(offset)
                .ok_or("Invalid playback position")?;
            let accepted = session
                .TryChangePlaybackPositionAsync(ticks)
                .map_err(|error| error.to_string())?
                .join()
                .map_err(|error| error.to_string())?;
            if accepted {
                Ok(())
            } else {
                Err("The active media session rejected seeking".into())
            }
        })
    })
    .await
    .map_err(|error| error.to_string())?
}

#[cfg(test)]
mod tests {
    use super::source_label;

    #[test]
    fn gives_common_media_session_ids_readable_names() {
        assert_eq!(source_label("Spotify.exe"), "Spotify");
        assert_eq!(
            source_label("Microsoft.MicrosoftEdge_123!MSEdge"),
            "Microsoft Edge"
        );
        assert_eq!(source_label("Vendor.Player_123!Player"), "Player");
    }
}

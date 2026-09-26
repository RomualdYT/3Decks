//! Spotify and Music playback via their public scripting dictionaries.
//! Apple Events still require the user's Automation permission.
use objc2::rc::Retained;
use objc2_app_kit::NSWorkspace;
use objc2_foundation::{NSAppleEventDescriptor, NSAppleEventSendOptions, NSString};
use serde_json::{json, Value};
use std::{
    ptr::NonNull,
    sync::{Arc, Mutex},
};

static ARTWORK_CACHE: Mutex<Option<(String, Arc<[u8]>)>> = Mutex::new(None);

fn code(bytes: &[u8; 4]) -> u32 {
    u32::from_be_bytes(*bytes)
}

fn property(
    code_value: u32,
    container: Option<&NSAppleEventDescriptor>,
) -> Result<Retained<NSAppleEventDescriptor>, String> {
    let record = NSAppleEventDescriptor::recordDescriptor();
    record.setDescriptor_forKeyword(
        &NSAppleEventDescriptor::descriptorWithTypeCode(code(b"prop")),
        code(b"want"),
    );
    record.setDescriptor_forKeyword(
        &NSAppleEventDescriptor::descriptorWithEnumCode(code(b"prop")),
        code(b"form"),
    );
    record.setDescriptor_forKeyword(
        &NSAppleEventDescriptor::descriptorWithTypeCode(code_value),
        code(b"seld"),
    );
    let null = NSAppleEventDescriptor::nullDescriptor();
    record.setDescriptor_forKeyword(container.unwrap_or(&null), code(b"from"));
    record
        .coerceToDescriptorType(code(b"obj "))
        .ok_or("Unable to construct Apple Event property".into())
}

fn element(
    class_code: u32,
    index: i32,
    container: &NSAppleEventDescriptor,
) -> Result<Retained<NSAppleEventDescriptor>, String> {
    let record = NSAppleEventDescriptor::recordDescriptor();
    record.setDescriptor_forKeyword(
        &NSAppleEventDescriptor::descriptorWithTypeCode(class_code),
        code(b"want"),
    );
    record.setDescriptor_forKeyword(
        &NSAppleEventDescriptor::descriptorWithEnumCode(code(b"indx")),
        code(b"form"),
    );
    record.setDescriptor_forKeyword(
        &NSAppleEventDescriptor::descriptorWithInt32(index),
        code(b"seld"),
    );
    record.setDescriptor_forKeyword(container, code(b"from"));
    record
        .coerceToDescriptorType(code(b"obj "))
        .ok_or("Unable to construct Apple Event element".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn property_specifier_contains_the_requested_property() {
        let descriptor = property(code(b"pTrk"), None).unwrap();
        assert_eq!(descriptor.descriptorType(), code(b"obj "));
        assert!(descriptor.data().length() > 0);
    }

    #[test]
    fn artwork_element_specifier_contains_an_index_and_track_container() {
        let track = property(code(b"pTrk"), None).unwrap();
        let descriptor = element(code(b"cArt"), 1, &track).unwrap();
        assert_eq!(descriptor.descriptorType(), code(b"obj "));
        assert!(descriptor.data().length() > 0);
    }
}

fn send(
    player: Player,
    event_class: u32,
    event_id: u32,
    direct: &NSAppleEventDescriptor,
    data: Option<&NSAppleEventDescriptor>,
) -> Result<Retained<NSAppleEventDescriptor>, String> {
    let target = NSAppleEventDescriptor::descriptorWithBundleIdentifier(&NSString::from_str(
        player.bundle_id(),
    ));
    let event = NSAppleEventDescriptor::appleEventWithEventClass_eventID_targetDescriptor_returnID_transactionID(
        event_class, event_id, Some(&target), -1, 0);
    event.setParamDescriptor_forKeyword(direct, code(b"----"));
    if let Some(data) = data {
        event.setParamDescriptor_forKeyword(data, code(b"data"));
    }
    let reply = event
        .sendEventWithOptions_timeout_error(NSAppleEventSendOptions::WaitForReply, 1.5)
        .map_err(|error| format!("{}: {}", player.name(), error.localizedDescription()))?;
    if let Some(error) = reply.paramDescriptorForKeyword(code(b"errn")) {
        if error.int32Value() != 0 {
            return Err(format!(
                "{} Apple Event error {}",
                player.name(),
                error.int32Value()
            ));
        }
    }
    Ok(reply)
}

fn get(
    player: Player,
    property_code: &[u8; 4],
    container: Option<&NSAppleEventDescriptor>,
) -> Result<Retained<NSAppleEventDescriptor>, String> {
    let specifier = property(code(property_code), container)?;
    send(player, code(b"core"), code(b"getd"), &specifier, None)?
        .paramDescriptorForKeyword(code(b"----"))
        .ok_or_else(|| format!("{} did not return a property", player.name()))
}

fn set(
    player: Player,
    property_code: &[u8; 4],
    value: &NSAppleEventDescriptor,
) -> Result<(), String> {
    let specifier = property(code(property_code), None)?;
    send(
        player,
        code(b"core"),
        code(b"setd"),
        &specifier,
        Some(value),
    )
    .map(|_| ())
}

fn string(value: &NSAppleEventDescriptor) -> String {
    value
        .stringValue()
        .map(|text| text.to_string())
        .unwrap_or_default()
}

fn real(value: &NSAppleEventDescriptor) -> f64 {
    value
        .coerceToDescriptorType(code(b"doub"))
        .map(|number| number.doubleValue())
        .unwrap_or_else(|| value.int32Value() as f64)
}

pub struct MediaSnapshot {
    pub media: Value,
    pub app_volume: Option<u8>,
    pub artwork_key: Option<String>,
    pub artwork: Option<Arc<[u8]>>,
}

fn artwork_data(track: &NSAppleEventDescriptor, key: &str) -> Result<Arc<[u8]>, String> {
    if let Some((cached_key, bytes)) = ARTWORK_CACHE.lock().unwrap().as_ref() {
        if cached_key == key {
            return Ok(bytes.clone());
        }
    }
    const MAX_ARTWORK_BYTES: usize = 4 * 1024 * 1024;
    let first_artwork = element(code(b"cArt"), 1, track)?;
    let descriptor = get(Player::Music, b"pRaw", Some(&first_artwork))?;
    let data = descriptor.data();
    let length = usize::try_from(data.length()).map_err(|_| "Invalid artwork length")?;
    if length == 0 || length > MAX_ARTWORK_BYTES {
        return Err("Music artwork is empty or too large".into());
    }
    let mut bytes = vec![0; length];
    let pointer = NonNull::new(bytes.as_mut_ptr().cast()).ok_or("Invalid artwork buffer")?;
    // NSData copies the complete descriptor payload into this owned buffer.
    unsafe { data.getBytes_length(pointer, length) };
    let bytes: Arc<[u8]> = bytes.into();
    *ARTWORK_CACHE.lock().unwrap() = Some((key.to_owned(), bytes.clone()));
    Ok(bytes)
}

fn inspect(player: Player, include_artwork: bool) -> Result<MediaSnapshot, String> {
    let state = get(player, b"pPlS", None)?;
    let volume = get(player, b"pVol", None)
        .ok()
        .map(|value| value.int32Value().clamp(0, 100) as u8);
    let track = property(code(b"pTrk"), None)?;
    let title = get(player, b"pnam", Some(&track))
        .map(|value| string(&value))
        .unwrap_or_default();
    if title.is_empty() {
        return Ok(MediaSnapshot {
            media: Value::Null,
            app_volume: volume,
            artwork_key: None,
            artwork: None,
        });
    }
    let artist = get(player, b"pArt", Some(&track))
        .map(|value| string(&value))
        .unwrap_or_default();
    let album = get(player, b"pAlb", Some(&track))
        .map(|value| string(&value))
        .unwrap_or_default();
    let duration = get(player, b"pDur", Some(&track))
        .map(|value| real(&value))
        .unwrap_or(0.0);
    let duration = if duration > 10_000.0 {
        duration / 1000.0
    } else {
        duration
    };
    let position = get(player, b"pPos", None)
        .map(|value| real(&value))
        .unwrap_or(0.0);
    let mut media = json!({"app":if matches!(player, Player::Music) {"Apple Music"} else {"Spotify"},
        "playing":state.enumCodeValue() == code(b"kPSP"), "title":title, "artist":artist, "album":album});
    if duration.is_finite() && duration > 0.0 {
        media["duration"] = json!(duration as u64);
        media["seekable"] = json!(true);
        if position.is_finite() {
            media["position"] = json!(position.clamp(0.0, duration) as u64);
        }
    }
    if include_artwork && matches!(player, Player::Spotify) {
        media["art_url"] = json!(get(player, b"aUrl", Some(&track))
            .map(|value| string(&value))
            .unwrap_or_default());
    }
    let artwork_key = format!("{}\0{}\0{}\0{}", player.name(), title, artist, album);
    let artwork = if include_artwork && matches!(player, Player::Music) {
        artwork_data(&track, &artwork_key).ok()
    } else {
        None
    };
    Ok(MediaSnapshot {
        media,
        app_volume: volume,
        artwork_key: artwork.as_ref().map(|_| artwork_key),
        artwork,
    })
}

pub async fn snapshot(include_artwork: bool) -> Result<Option<MediaSnapshot>, String> {
    tokio::task::spawn_blocking(move || match running_player() {
        Some(player) => inspect(player, include_artwork).map(Some),
        None => Ok(None),
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn volume() -> Result<u8, String> {
    tokio::task::spawn_blocking(|| {
        let player = running_player().ok_or("No supported media player is running")?;
        let value = get(player, b"pVol", None)?;
        Ok(value.int32Value().clamp(0, 100) as u8)
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn set_volume(value: u8) -> Result<(), String> {
    tokio::task::spawn_blocking(move || {
        let player = running_player().ok_or("No supported media player is running")?;
        set(
            player,
            b"pVol",
            &NSAppleEventDescriptor::descriptorWithInt32(i32::from(value)),
        )
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn seek(seconds: f64) -> Result<(), String> {
    if !seconds.is_finite() || seconds < 0.0 || seconds > 3600.0 {
        return Err("Invalid playback position".into());
    }
    tokio::task::spawn_blocking(move || {
        let player = running_player().ok_or("No supported media player is running")?;
        set(
            player,
            b"pPos",
            &NSAppleEventDescriptor::descriptorWithDouble(seconds),
        )
    })
    .await
    .map_err(|error| error.to_string())?
}

#[derive(Clone, Copy)]
enum Player {
    Spotify,
    Music,
}

impl Player {
    fn bundle_id(self) -> &'static str {
        match self {
            Self::Spotify => "com.spotify.client",
            Self::Music => "com.apple.Music",
        }
    }

    fn name(self) -> &'static str {
        match self {
            Self::Spotify => "Spotify",
            Self::Music => "Music",
        }
    }

    fn event(self, command: &str) -> Result<(u32, u32), String> {
        // Four-character Apple Event codes from Spotify.sdef and com.apple.Music.sdef.
        let (suite, code) = match (self, command) {
            (Self::Spotify, "playpause") => (b"spfy", b"PlPs"),
            (Self::Spotify, "next track") => (b"spfy", b"Next"),
            (Self::Spotify, "previous track") => (b"spfy", b"Prev"),
            (Self::Music, "playpause") => (b"hook", b"PlPs"),
            (Self::Music, "next track") => (b"hook", b"Next"),
            (Self::Music, "previous track") => (b"hook", b"Prev"),
            _ => return Err("Unsupported media command".into()),
        };
        Ok((u32::from_be_bytes(*suite), u32::from_be_bytes(*code)))
    }
}

fn running_player() -> Option<Player> {
    let workspace = NSWorkspace::sharedWorkspace();
    let applications = workspace.runningApplications();
    let running: Vec<Player> = [Player::Spotify, Player::Music]
        .into_iter()
        .filter(|player| {
            applications.iter().any(|app| {
                app.bundleIdentifier()
                    .is_some_and(|identifier| identifier.to_string() == player.bundle_id())
            })
        })
        .collect();
    if running.len() <= 1 {
        return running.into_iter().next();
    }
    if let Some(playing) = running.iter().copied().find(|player| {
        get(*player, b"pPlS", None).is_ok_and(|state| state.enumCodeValue() == code(b"kPSP"))
    }) {
        return Some(playing);
    }
    let foreground = workspace
        .frontmostApplication()
        .and_then(|app| app.bundleIdentifier())
        .map(|identifier| identifier.to_string());
    running
        .iter()
        .copied()
        .find(|player| foreground.as_deref() == Some(player.bundle_id()))
        .or_else(|| running.into_iter().next())
}

pub async fn command(command: &str) -> Result<(), String> {
    let command = command.to_owned();
    tokio::task::spawn_blocking(move || {
        let player = running_player().ok_or("No supported media player is running")?;
        let (event_class, event_id) = player.event(&command)?;
        let target = NSAppleEventDescriptor::descriptorWithBundleIdentifier(
            &NSString::from_str(player.bundle_id()),
        );
        let event = NSAppleEventDescriptor::appleEventWithEventClass_eventID_targetDescriptor_returnID_transactionID(
            event_class, event_id, Some(&target), -1, 0,
        );
        event.sendEventWithOptions_timeout_error(NSAppleEventSendOptions::WaitForReply, 3.0)
            .map(|_| ())
            .map_err(|error| format!("{}: {}", player.name(), error.localizedDescription()))
    }).await.map_err(|error| error.to_string())?
}

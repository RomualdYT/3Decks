//! Spotify and Music playback via their public scripting dictionaries.
//! Apple Events still require the user's Automation permission.
use objc2_app_kit::NSWorkspace;
use objc2_foundation::{NSAppleEventDescriptor, NSAppleEventSendOptions, NSString};

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
    let applications = NSWorkspace::sharedWorkspace().runningApplications();
    [Player::Spotify, Player::Music].into_iter().find(|player| {
        applications.iter().any(|app| {
            app.bundleIdentifier()
                .is_some_and(|identifier| identifier.to_string() == player.bundle_id())
        })
    })
}

pub async fn active_player() -> Option<&'static str> {
    tokio::task::spawn_blocking(|| running_player().map(Player::name))
        .await
        .ok()
        .flatten()
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

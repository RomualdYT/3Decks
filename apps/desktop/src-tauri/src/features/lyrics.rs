//! Optional synchronized lyrics. Only the desktop contacts LRCLIB; the console
//! receives bounded, timestamped lines and follows its local monotonic clock.
use crate::app::state::Shared;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    path::Path,
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
    time::{Duration, Instant},
};
use tokio::sync::{broadcast, Mutex};

const MAX_LINES: usize = 256;
const MAX_LINE_BYTES: usize = 120;
const MAX_RESPONSE_BYTES: usize = 256 * 1024;

#[derive(Clone, Debug, PartialEq, Eq)]
struct Track {
    title: String,
    artist: String,
    album: String,
    duration: u64,
}

impl Track {
    fn from_state(state: &Value) -> Option<Self> {
        let media = &state["media"];
        let title = media["title"].as_str()?.trim();
        let artist = media["artist"].as_str()?.trim();
        if title.is_empty() || artist.is_empty() || title.len() > 200 || artist.len() > 200 {
            return None;
        }
        Some(Self {
            title: title.to_owned(),
            artist: artist.to_owned(),
            album: media["album"]
                .as_str()
                .unwrap_or("")
                .chars()
                .take(200)
                .collect(),
            duration: media["duration"].as_u64().unwrap_or(0),
        })
    }

    fn filename(&self) -> String {
        let digest = Sha256::digest(
            format!(
                "{}\0{}\0{}\0{}",
                self.title.to_lowercase(),
                self.artist.to_lowercase(),
                self.album.to_lowercase(),
                self.duration
            )
            .as_bytes(),
        );
        hex::encode(digest)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Line {
    pub t: u32,
    pub text: String,
}

fn bounded_text(input: &str) -> String {
    let mut output = String::new();
    for character in input.trim().chars() {
        if character.is_control() {
            continue;
        }
        if output.len() + character.len_utf8() > MAX_LINE_BYTES {
            break;
        }
        output.push(character);
    }
    output
}

pub fn parse_lrc(input: &str) -> Vec<Line> {
    let mut lines = Vec::new();
    for row in input.lines() {
        let mut rest = row.trim();
        let mut times = Vec::new();
        while let Some(after_open) = rest.strip_prefix('[') {
            let Some((stamp, after_close)) = after_open.split_once(']') else {
                break;
            };
            let Some((minutes, seconds)) = stamp.split_once(':') else {
                break;
            };
            let (Ok(minutes), Ok(seconds)) = (minutes.parse::<u32>(), seconds.parse::<f64>())
            else {
                break;
            };
            if minutes > 59 || !seconds.is_finite() || !(0.0..60.0).contains(&seconds) {
                break;
            }
            times.push(
                minutes
                    .saturating_mul(60_000)
                    .saturating_add((seconds * 1000.0).round() as u32),
            );
            rest = after_close;
        }
        let text = bounded_text(rest);
        if text.is_empty() {
            continue;
        }
        for t in times {
            if lines.len() >= MAX_LINES {
                break;
            }
            lines.push(Line {
                t,
                text: text.clone(),
            });
        }
        if lines.len() >= MAX_LINES {
            break;
        }
    }
    lines.sort_by_key(|line| line.t);
    lines
}

fn publish(shared: &Shared, message: Value) {
    *shared.latest_lyrics.write().unwrap() = message.clone();
    let _ = shared.lyrics_updates.send(message);
}

fn message(track: Option<&Track>, status: &str, lines: Vec<Line>) -> Value {
    let mut value = json!({"type":"media.lyrics","status":status,"lines":lines});
    if let Some(track) = track {
        value["track"] = json!(track.title);
        value["artist"] = json!(track.artist);
        value["duration_ms"] = json!(track.duration.saturating_mul(1000));
    }
    value
}

async fn read_lines(path: &Path) -> Option<Vec<Line>> {
    let bytes = tokio::fs::read(path).await.ok()?;
    if bytes.len() > MAX_RESPONSE_BYTES {
        return None;
    }
    if path.extension().is_some_and(|extension| extension == "lrc") {
        Some(parse_lrc(std::str::from_utf8(&bytes).ok()?))
    } else {
        serde_json::from_slice::<Vec<Line>>(&bytes)
            .ok()
            .filter(|lines| {
                lines.len() <= MAX_LINES
                    && lines.iter().all(|line| line.text.len() <= MAX_LINE_BYTES)
            })
    }
}

async fn lookup(
    client: &reqwest::Client,
    directory: &Path,
    track: &Track,
    online: bool,
    next_request: &Mutex<Instant>,
) -> Result<(String, Vec<Line>), String> {
    let stem = track.filename();
    if let Some(lines) = read_lines(&directory.join(format!("{stem}.lrc"))).await {
        return Ok((
            if lines.is_empty() {
                "unsynced"
            } else {
                "ready"
            }
            .into(),
            lines,
        ));
    }
    if !online {
        return Ok(("disabled".into(), vec![]));
    }
    if let Some(lines) = read_lines(&directory.join(format!("{stem}.json"))).await {
        return Ok(("ready".into(), lines));
    }
    {
        let mut next = next_request.lock().await;
        if *next > Instant::now() {
            tokio::time::sleep_until(tokio::time::Instant::from_std(*next)).await;
        }
        *next = Instant::now() + Duration::from_millis(350);
    }
    let mut query = vec![
        ("track_name", track.title.clone()),
        ("artist_name", track.artist.clone()),
    ];
    if !track.album.is_empty() {
        query.push(("album_name", track.album.clone()));
    }
    if (1..=3600).contains(&track.duration) {
        query.push(("duration", track.duration.to_string()));
    }
    let mut url =
        url::Url::parse("https://lrclib.net/api/get").map_err(|error| error.to_string())?;
    url.query_pairs_mut().extend_pairs(query);
    let response = client
        .get(url)
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if response.status() == reqwest::StatusCode::NOT_FOUND {
        return Ok(("unavailable".into(), vec![]));
    }
    if response.status() == reqwest::StatusCode::TOO_MANY_REQUESTS {
        let retry = response
            .headers()
            .get(reqwest::header::RETRY_AFTER)
            .and_then(|value| value.to_str().ok())
            .unwrap_or("60");
        let delay = retry.parse::<u64>().unwrap_or(60).clamp(1, 3600);
        *next_request.lock().await = Instant::now() + Duration::from_secs(delay);
        return Err(format!("LRCLIB rate limit; retry after {delay}s"));
    }
    let mut response = response
        .error_for_status()
        .map_err(|error| error.to_string())?;
    if response
        .content_length()
        .is_some_and(|length| length > MAX_RESPONSE_BYTES as u64)
    {
        return Err("Lyrics response is too large".into());
    }
    let mut bytes = Vec::new();
    while let Some(chunk) = response.chunk().await.map_err(|error| error.to_string())? {
        if bytes.len().saturating_add(chunk.len()) > MAX_RESPONSE_BYTES {
            return Err("Lyrics response is too large".into());
        }
        bytes.extend_from_slice(&chunk);
    }
    let body: Value = serde_json::from_slice(&bytes).map_err(|error| error.to_string())?;
    if body["instrumental"].as_bool() == Some(true) {
        return Ok(("instrumental".into(), vec![]));
    }
    let Some(lrc) = body["syncedLyrics"].as_str() else {
        return Ok(("unsynced".into(), vec![]));
    };
    let lines = parse_lrc(lrc);
    if lines.is_empty() {
        return Ok(("unsynced".into(), vec![]));
    }
    let encoded = serde_json::to_vec(&lines).map_err(|error| error.to_string())?;
    let _ = tokio::fs::create_dir_all(directory).await;
    let _ = tokio::fs::write(directory.join(format!("{stem}.json")), encoded).await;
    Ok(("ready".into(), lines))
}

pub async fn run(shared: Arc<Shared>) {
    let _ = rustls::crypto::ring::default_provider().install_default();
    let Ok(directory) = shared.lyrics_directory() else {
        return;
    };
    let client = match reqwest::Client::builder()
        .user_agent(concat!(
            "3Decks/",
            env!("CARGO_PKG_VERSION"),
            " (https://github.com/RomualdYT/3Decks)"
        ))
        .timeout(Duration::from_secs(8))
        .build()
    {
        Ok(client) => client,
        Err(_) => return,
    };
    let mut updates = shared.state_updates.subscribe();
    let mut config_updates = shared.config_updates.subscribe();
    let mut stop = shared.stop.subscribe();
    let generation = Arc::new(AtomicU64::new(0));
    let next_request = Arc::new(Mutex::new(Instant::now()));
    let mut current: Option<(Track, bool)> = None;
    let mut task: Option<tokio::task::JoinHandle<()>> = None;
    loop {
        tokio::select! {
            changed = stop.changed() => { if changed.is_err() || *stop.borrow() { break; } }
            _ = config_updates.changed() => {}
            result = updates.recv() => { if result.is_err() && !matches!(result, Err(broadcast::error::RecvError::Lagged(_))) { break; } }
        }
        let config = shared.config.document();
        let enabled = config["features"]["lyrics_online"].as_bool() == Some(true);
        let wanted = config["pages"]
            .as_array()
            .is_some_and(|pages| pages.iter().any(|page| page["dashboard"] == "lyrics"));
        let track = if wanted {
            Track::from_state(&shared.latest_state.read().unwrap())
        } else {
            None
        };
        let next = track.clone().map(|track| (track, enabled));
        if current == next {
            continue;
        }
        current = next;
        let token = generation.fetch_add(1, Ordering::SeqCst) + 1;
        if let Some(task) = task.take() {
            task.abort();
        }
        let Some(track) = track else {
            publish(&shared, message(None, "idle", vec![]));
            continue;
        };
        publish(&shared, message(Some(&track), "loading", vec![]));
        let shared = shared.clone();
        let client = client.clone();
        let directory = directory.clone();
        let generation = generation.clone();
        let next_request = next_request.clone();
        task = Some(tokio::spawn(async move {
            let result = lookup(&client, &directory, &track, enabled, &next_request).await;
            if generation.load(Ordering::SeqCst) != token {
                return;
            }
            let payload = match result {
                Ok((status, lines)) => message(Some(&track), &status, lines),
                Err(error) => {
                    crate::app::logging::append(&format!("Lyrics lookup: {error}"));
                    message(Some(&track), "error", vec![])
                }
            };
            if serde_json::to_vec(&payload)
                .is_ok_and(|bytes| bytes.len() <= crate::transport::protocol::MAX_MESSAGE)
            {
                publish(&shared, payload);
            } else {
                publish(&shared, message(Some(&track), "too_large", vec![]));
            }
        }));
    }
    if let Some(task) = task {
        task.abort();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lrc_parser_sorts_timestamps_and_bounds_utf8() {
        let lines =
            parse_lrc("[00:02.50] après\n[00:01.00][00:03.00]été\n[ar:metadata]\n[00:04.00] ");
        assert_eq!(
            lines.iter().map(|line| line.t).collect::<Vec<_>>(),
            vec![1000, 2500, 3000]
        );
        assert_eq!(lines[1].text, "après");
        assert!(
            parse_lrc(&format!("[00:01.00]{}", "é".repeat(200)))[0]
                .text
                .len()
                <= MAX_LINE_BYTES
        );
    }

    #[test]
    fn track_key_includes_duration_and_album() {
        let mut track = Track {
            title: "Song".into(),
            artist: "Artist".into(),
            album: "Album".into(),
            duration: 180,
        };
        let first = track.filename();
        track.duration = 181;
        assert_ne!(first, track.filename());
    }

    #[tokio::test]
    async fn disabling_online_lyrics_hides_cache_but_keeps_local_lrc() {
        let _ = rustls::crypto::ring::default_provider().install_default();
        let track = Track {
            title: "Song".into(),
            artist: "Artist".into(),
            album: String::new(),
            duration: 180,
        };
        let directory =
            std::env::temp_dir().join(format!("3decks-lyrics-{}", rand::random::<u64>()));
        tokio::fs::create_dir_all(&directory).await.unwrap();
        let stem = track.filename();
        tokio::fs::write(
            directory.join(format!("{stem}.json")),
            r#"[{"t":1000,"text":"cached"}]"#,
        )
        .await
        .unwrap();
        let client = reqwest::Client::new();
        let next_request = Mutex::new(Instant::now());
        let disabled = lookup(&client, &directory, &track, false, &next_request)
            .await
            .unwrap();
        assert_eq!(disabled.0, "disabled");
        assert!(disabled.1.is_empty());
        tokio::fs::write(directory.join(format!("{stem}.lrc")), "[00:02.00]local")
            .await
            .unwrap();
        let local = lookup(&client, &directory, &track, false, &next_request)
            .await
            .unwrap();
        assert_eq!(local.1[0].text, "local");
        let _ = tokio::fs::remove_dir_all(directory).await;
    }
}

//! Official Twitch badge resolution and bounded, asynchronous console image cache.
use super::{Service, model::text, storage::Credentials, twitch};
use futures_util::StreamExt;
use serde::Serialize;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    collections::{HashMap, HashSet, VecDeque},
    time::{Duration, Instant},
};

pub const PER_MESSAGE: usize = 3;
const CACHE_LIMIT: usize = 64;
const SIDE: usize = 16;
const MAX_BYTES: usize = 128 * 1024;

#[derive(Clone, Serialize)]
pub struct Badge {
    pub token: u32,
    pub title: String,
    pub image: String,
}

pub fn valid_image(raw: &str) -> bool {
    url::Url::parse(raw).is_ok_and(|url| {
        raw.len() <= 200
            && url.scheme() == "https"
            && url.host_str() == Some("static-cdn.jtvnw.net")
            && url.path().starts_with("/badges/v1/")
            && url.port().is_none()
            && url.username().is_empty()
            && url.password().is_none()
            && url.query().is_none()
            && url.fragment().is_none()
    })
}

#[derive(Default)]
pub struct Catalog(HashMap<(String, String), Badge>);

impl Catalog {
    pub async fn load(client: &reqwest::Client, credentials: &Credentials, channel: &str) -> Self {
        let mut catalog = Self::default();
        let (global, local) = tokio::join!(
            twitch::badge_catalog(client, credentials, None),
            twitch::badge_catalog(client, credentials, Some(channel)),
        );
        // Channel versions override global versions, particularly subscriber/bits badges.
        for raw in [global, local].into_iter().flatten() {
            let Some(sets) = raw["data"].as_array() else {
                continue;
            };
            for set in sets.iter().take(256) {
                let Some(id) = set["set_id"].as_str() else {
                    continue;
                };
                let Some(versions) = set["versions"].as_array() else {
                    continue;
                };
                for version in versions.iter().take(512) {
                    let Some(version_id) = version["id"].as_str() else {
                        continue;
                    };
                    let image = version["image_url_2x"].as_str().unwrap_or("");
                    if id.len() > 64 || version_id.len() > 64 || !valid_image(image) {
                        continue;
                    }
                    let hash = Sha256::digest(image.as_bytes());
                    let token =
                        (u32::from_le_bytes(hash[..4].try_into().unwrap()) & 0x7fff_ffff).max(1);
                    if catalog.0.len() >= 4096
                        && !catalog.0.contains_key(&(id.into(), version_id.into()))
                    {
                        continue;
                    }
                    catalog.0.insert(
                        (id.into(), version_id.into()),
                        Badge {
                            token,
                            title: text(version["title"].as_str().unwrap_or(id), 64),
                            image: image.into(),
                        },
                    );
                }
            }
        }
        catalog
    }

    pub fn resolve(&self, raw: &Value) -> Vec<Badge> {
        raw.as_array()
            .into_iter()
            .flatten()
            .filter_map(|badge| {
                let key = (
                    badge["set_id"].as_str()?.to_owned(),
                    badge["id"].as_str()?.to_owned(),
                );
                self.0.get(&key).cloned()
            })
            .take(PER_MESSAGE)
            .collect()
    }
}

struct Entry {
    token: u32,
    frame: Option<Vec<u8>>,
    retry_at: Instant,
}
#[derive(Default)]
pub struct Cache {
    entries: VecDeque<Entry>,
    pub revision: u64,
}
impl Cache {
    pub fn frame(&self, token: u32) -> Option<Vec<u8>> {
        self.entries
            .iter()
            .find(|entry| entry.token == token)?
            .frame
            .clone()
    }
    fn pending(&self, token: u32) -> bool {
        !self.entries.iter().any(|entry| {
            entry.token == token && (entry.frame.is_some() || entry.retry_at > Instant::now())
        })
    }
    fn insert(&mut self, token: u32, frame: Option<Vec<u8>>, active: &HashSet<u32>) {
        self.entries.retain(|entry| entry.token != token);
        if self.entries.len() >= CACHE_LIMIT {
            let index = self
                .entries
                .iter()
                .position(|entry| !active.contains(&entry.token))
                .unwrap_or(0);
            self.entries.remove(index);
        }
        if frame.is_some() {
            self.revision = self.revision.wrapping_add(1);
        }
        self.entries.push_back(Entry {
            token,
            frame,
            retry_at: Instant::now() + Duration::from_secs(30),
        });
    }
}

fn decode(bytes: &[u8], token: u32) -> Option<Vec<u8>> {
    let reader = || {
        image::ImageReader::new(std::io::Cursor::new(bytes))
            .with_guessed_format()
            .ok()
    };
    let (width, height) = reader()?.into_dimensions().ok()?;
    if width == 0 || height == 0 || width > 256 || height > 256 {
        return None;
    }
    let pixels = reader()?
        .decode()
        .ok()?
        .resize_exact(
            SIDE as u32,
            SIDE as u32,
            image::imageops::FilterType::Lanczos3,
        )
        .to_rgba8();
    let mut frame = vec![0; 12 + SIDE * SIDE * 4];
    frame[..4].copy_from_slice(b"BDG0");
    frame[4..6].copy_from_slice(&(SIDE as u16).to_le_bytes());
    frame[6..8].copy_from_slice(&(SIDE as u16).to_le_bytes());
    frame[8..12].copy_from_slice(&token.to_le_bytes());
    for (x, y, pixel) in pixels.enumerate_pixels() {
        let (x, y) = (x as usize, y as usize);
        let tile = (y / 8) * (SIDE / 8) + x / 8;
        let mut morton = 0;
        for bit in 0..3 {
            morton |= ((x >> bit) & 1) << (2 * bit);
            morton |= ((y >> bit) & 1) << (2 * bit + 1);
        }
        let offset = 12 + (tile * 64 + morton) * 4;
        // PICA200 RGBA8 stores little-endian ABGR bytes, retaining transparency.
        frame[offset..offset + 4].copy_from_slice(&[pixel[3], pixel[2], pixel[1], pixel[0]]);
    }
    Some(frame)
}

async fn download(client: &reqwest::Client, badge: &Badge) -> Option<Vec<u8>> {
    if !valid_image(&badge.image) {
        return None;
    }
    // CDN requests intentionally carry no Twitch credentials.
    let response = client
        .get(&badge.image)
        .timeout(Duration::from_secs(3))
        .send()
        .await
        .ok()?
        .error_for_status()
        .ok()?;
    if response
        .content_length()
        .is_some_and(|size| size > MAX_BYTES as u64)
    {
        return None;
    }
    let mut stream = response.bytes_stream();
    let mut bytes = Vec::new();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.ok()?;
        if bytes.len() + chunk.len() > MAX_BYTES {
            return None;
        }
        bytes.extend_from_slice(&chunk);
    }
    let token = badge.token;
    tokio::task::spawn_blocking(move || decode(&bytes, token))
        .await
        .ok()?
}

pub async fn run(service: &Service) {
    let mut tick = tokio::time::interval(Duration::from_millis(250));
    tick.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
    loop {
        tick.tick().await;
        let badges: Vec<Badge> = service
            .snapshot
            .read()
            .unwrap()
            .messages
            .iter()
            .rev()
            .flat_map(|message| message.badges.clone())
            .collect();
        let active: HashSet<u32> = badges.iter().map(|badge| badge.token).collect();
        for badge in badges {
            if !service.badges.lock().unwrap().pending(badge.token) {
                continue;
            }
            let frame = download(&service.http, &badge).await;
            service
                .badges
                .lock()
                .unwrap()
                .insert(badge.token, frame, &active);
            // Re-read current history after every download: never drain a stale channel queue.
            break;
        }
    }
}

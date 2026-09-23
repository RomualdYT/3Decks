//! Album art transfer for the 3DS: 128×128 RGB565 pixels in Morton tiles.
//! Image conversion happens only when the media source changes.

use std::sync::{Arc, Mutex};

const SIDE: usize = 128;
const TEXTURE_BYTES: usize = SIDE * SIDE * 2;

#[derive(Default)]
pub struct ArtworkCache {
    url: String,
    token: u32,
    texture: Option<Vec<u8>>,
    preview: Option<Vec<u8>>,
    accent: String,
}

impl ArtworkCache {
    pub fn preview(&self) -> Option<Vec<u8>> {
        self.preview.clone()
    }

    pub fn decorate(&self, media: &mut serde_json::Value) {
        if self.texture.is_some() && self.token != 0 {
            media["art"] = serde_json::json!(self.token);
            if !self.accent.is_empty() {
                media["accent"] = serde_json::json!(self.accent);
            }
        }
    }

    pub fn frame_for_token(&self, token: u32) -> Option<Vec<u8>> {
        if token == 0 || token != self.token {
            return None;
        }
        let texture = self.texture.as_ref()?;
        let mut frame = Vec::with_capacity(12 + TEXTURE_BYTES);
        frame.extend_from_slice(b"ART0");
        frame.extend_from_slice(&(SIDE as u16).to_le_bytes());
        frame.extend_from_slice(&(SIDE as u16).to_le_bytes());
        frame.extend_from_slice(&token.to_le_bytes());
        frame.extend_from_slice(texture);
        Some(frame)
    }
}

pub async fn refresh(cache: Arc<Mutex<ArtworkCache>>, url: &str) {
    let current = {
        let mut cache = cache.lock().unwrap();
        if cache.url == url {
            return;
        }
        cache.url = url.to_owned();
        cache.token = 0;
        cache.texture = None;
        cache.preview = None;
        cache.accent.clear();
        cache.url.clone()
    };
    if current.is_empty() {
        return;
    }
    #[cfg(target_os = "macos")]
    {
        if let Ok((texture, preview, accent)) = prepare(&current).await {
            let mut cache = cache.lock().unwrap();
            if cache.url == current {
                cache.token = token_for(&current);
                cache.texture = Some(texture);
                cache.preview = preview;
                cache.accent = accent;
            }
        }
    }
}

fn token_for(url: &str) -> u32 {
    let mut crc = !0_u32;
    for byte in url.bytes() {
        crc ^= u32::from(byte);
        for _ in 0..8 {
            crc = (crc >> 1) ^ (0xedb8_8320 & (0_u32.wrapping_sub(crc & 1)));
        }
    }
    !crc & 0x7fff_ffff
}

fn morton(x: usize, y: usize) -> usize {
    let mut offset = 0;
    for bit in 0..3 {
        offset |= ((x >> bit) & 1) << (2 * bit);
        offset |= ((y >> bit) & 1) << (2 * bit + 1);
    }
    offset
}

fn texture_from_pixels(pixels: &[u8], samples: usize) -> Option<(Vec<u8>, String)> {
    if !matches!(samples, 3 | 4) || pixels.len() < SIDE * SIDE * samples {
        return None;
    }
    let mut texture = vec![0_u8; TEXTURE_BYTES];
    let mut red_sum = 0_u64;
    let mut green_sum = 0_u64;
    let mut blue_sum = 0_u64;
    for y in 0..SIDE {
        for x in 0..SIDE {
            let source = (y * SIDE + x) * samples;
            let (r, g, b) = (pixels[source], pixels[source + 1], pixels[source + 2]);
            let pixel = (u16::from(r >> 3) << 11) | (u16::from(g >> 2) << 5) | u16::from(b >> 3);
            let tile = (y / 8) * (SIDE / 8) + (x / 8);
            let offset = (tile * 64 + morton(x % 8, y % 8)) * 2;
            texture[offset..offset + 2].copy_from_slice(&pixel.to_le_bytes());
            red_sum += u64::from(r);
            green_sum += u64::from(g);
            blue_sum += u64::from(b);
        }
    }
    let count = (SIDE * SIDE) as u64;
    let accent = format!(
        "#{:02X}{:02X}{:02X}",
        red_sum / count,
        green_sum / count,
        blue_sum / count
    );
    Some((texture, accent))
}

#[cfg(target_os = "macos")]
fn tiff_pixels(data: &[u8]) -> Option<(Vec<u8>, usize)> {
    let little = match data.get(..2)? {
        b"II" => true,
        b"MM" => false,
        _ => return None,
    };
    let read16 = |offset: usize| {
        let bytes: [u8; 2] = data.get(offset..offset + 2)?.try_into().ok()?;
        Some(if little {
            u16::from_le_bytes(bytes)
        } else {
            u16::from_be_bytes(bytes)
        })
    };
    let read32 = |offset: usize| {
        let bytes: [u8; 4] = data.get(offset..offset + 4)?.try_into().ok()?;
        Some(if little {
            u32::from_le_bytes(bytes)
        } else {
            u32::from_be_bytes(bytes)
        })
    };
    if read16(2)? != 42 {
        return None;
    }
    let ifd = read32(4)? as usize;
    let count = read16(ifd)? as usize;
    let mut compression = 1_u32;
    let mut samples = 3_usize;
    let mut strip = None;
    for index in 0..count.min(128) {
        let offset = ifd.checked_add(2 + index * 12)?;
        let tag = read16(offset)?;
        let kind = read16(offset + 2)?;
        let quantity = read32(offset + 4)?;
        let value = if kind == 3 && quantity == 1 {
            u32::from(read16(offset + 8)?)
        } else {
            read32(offset + 8)?
        };
        match tag {
            259 => compression = value,
            273 => strip = Some(value as usize),
            277 => samples = value as usize,
            _ => {}
        }
    }
    if compression != 1 || !matches!(samples, 3 | 4) {
        return None;
    }
    let start = strip?;
    let end = start.checked_add(SIDE * SIDE * samples)?;
    Some((data.get(start..end)?.to_vec(), samples))
}

#[cfg(target_os = "macos")]
async fn prepare(url: &str) -> Result<(Vec<u8>, Option<Vec<u8>>, String), String> {
    use std::{fs, os::unix::fs::DirBuilderExt, path::PathBuf, time::Duration};
    use tokio::process::Command;

    struct Scratch(PathBuf);
    impl Drop for Scratch {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }
    let folder = std::env::temp_dir().join(format!(
        "3decks-art-{}-{}",
        std::process::id(),
        rand::random::<u64>()
    ));
    fs::DirBuilder::new()
        .mode(0o700)
        .create(&folder)
        .map_err(|error| error.to_string())?;
    let scratch = Scratch(folder);
    let source = scratch.0.join("source");
    let parsed = url::Url::parse(url).map_err(|error| error.to_string())?;
    match parsed.scheme() {
        "file" => {
            let path = parsed
                .to_file_path()
                .map_err(|_| "Invalid artwork file URL")?;
            let metadata = fs::metadata(&path).map_err(|error| error.to_string())?;
            if metadata.len() > 4 * 1024 * 1024 {
                return Err("Artwork file too large".into());
            }
            fs::copy(path, &source).map_err(|error| error.to_string())?;
        }
        "http" | "https" if parsed.username().is_empty() && parsed.password().is_none() => {
            let result = tokio::time::timeout(
                Duration::from_secs(7),
                Command::new("/usr/bin/curl")
                    .kill_on_drop(true)
                    .args([
                        "--fail",
                        "--silent",
                        "--show-error",
                        "--location",
                        "--max-time",
                        "6",
                        "--max-filesize",
                        "4194304",
                        "--proto",
                        "=http,https",
                        "--proto-redir",
                        "=http,https",
                        "--output",
                    ])
                    .arg(&source)
                    .arg(url)
                    .output(),
            )
            .await
            .map_err(|_| "Artwork download timed out")?
            .map_err(|error| error.to_string())?;
            if !result.status.success() {
                return Err("Artwork download failed".into());
            }
            if fs::metadata(&source)
                .map_err(|error| error.to_string())?
                .len()
                > 4 * 1024 * 1024
            {
                return Err("Artwork download too large".into());
            }
        }
        _ => return Err("Unsupported artwork URL".into()),
    }
    let tiff = scratch.0.join("resized.tiff");
    let result = tokio::time::timeout(
        Duration::from_secs(10),
        Command::new("/usr/bin/sips")
            .kill_on_drop(true)
            .arg("-z")
            .arg("128")
            .arg("128")
            .args(["-s", "format", "tiff", "-s", "formatOptions", "none"])
            .arg(&source)
            .arg("--out")
            .arg(&tiff)
            .output(),
    )
    .await
    .map_err(|_| "Artwork conversion timed out")?
    .map_err(|error| error.to_string())?;
    if !result.status.success() {
        return Err("Artwork conversion failed".into());
    }
    let (pixels, samples) = tiff_pixels(&fs::read(&tiff).map_err(|error| error.to_string())?)
        .ok_or("Unrecognized converted artwork")?;
    let (texture, accent) =
        texture_from_pixels(&pixels, samples).ok_or("Invalid artwork pixels")?;
    let preview_path = scratch.0.join("preview.png");
    let preview = match tokio::time::timeout(
        Duration::from_secs(5),
        Command::new("/usr/bin/sips")
            .kill_on_drop(true)
            .args(["-s", "format", "png"])
            .arg(&tiff)
            .arg("--out")
            .arg(&preview_path)
            .output(),
    )
    .await
    {
        Ok(Ok(result)) if result.status.success() => fs::read(preview_path).ok(),
        _ => None,
    };
    Ok((texture, preview, accent))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rgb565_morton_layout_matches_console_frame() {
        let mut pixels = vec![0_u8; SIDE * SIDE * 3];
        pixels[0..3].copy_from_slice(&[255, 0, 0]);
        let second = (1 * SIDE + 0) * 3;
        pixels[second..second + 3].copy_from_slice(&[0, 255, 0]);
        let (texture, _) = texture_from_pixels(&pixels, 3).unwrap();
        assert_eq!(&texture[0..2], &0xf800_u16.to_le_bytes());
        assert_eq!(&texture[4..6], &0x07e0_u16.to_le_bytes());
        let cache = ArtworkCache {
            url: "x".into(),
            token: 7,
            texture: Some(texture),
            preview: None,
            accent: "".into(),
        };
        let frame = cache.frame_for_token(7).unwrap();
        assert_eq!(&frame[..12], b"ART0\x80\x00\x80\x00\x07\x00\x00\x00");
        assert_eq!(frame.len(), 12 + TEXTURE_BYTES);
    }

    #[test]
    fn token_matches_python_crc32() {
        assert_eq!(token_for("https://example.com/cover.jpg"), 1_538_660_717);
    }

    #[cfg(target_os = "macos")]
    #[tokio::test]
    async fn converts_local_image_to_console_texture_and_preview() {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("icons/icon.png");
        let url = url::Url::from_file_path(path).unwrap();
        let (texture, preview, accent) = prepare(url.as_str()).await.unwrap();
        assert_eq!(texture.len(), TEXTURE_BYTES);
        assert!(preview.unwrap().starts_with(b"\x89PNG"));
        assert!(accent.starts_with('#'));
    }
}

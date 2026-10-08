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
    #[cfg(any(target_os = "macos", target_os = "windows"))]
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

pub async fn refresh_bytes(cache: Arc<Mutex<ArtworkCache>>, key: &str, bytes: &[u8]) {
    let identity = format!("media-art:{key}");
    {
        let mut cache = cache.lock().unwrap();
        if cache.url == identity {
            return;
        }
        cache.url = identity.clone();
        cache.token = 0;
        cache.texture = None;
        cache.preview = None;
        cache.accent.clear();
    }
    #[cfg(any(target_os = "macos", target_os = "windows"))]
    if let Ok((texture, preview, accent)) = prepare_bytes(bytes).await {
        let mut cache = cache.lock().unwrap();
        if cache.url == identity {
            cache.token = token_for(&identity);
            cache.texture = Some(texture);
            cache.preview = preview;
            cache.accent = accent;
        }
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    let _ = bytes;
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

const MAX_SOURCE_BYTES: usize = 4 * 1024 * 1024;
const MAX_IMAGE_PIXELS: u64 = 16 * 1024 * 1024;

fn image_reader(bytes: &[u8]) -> Result<image::ImageReader<std::io::Cursor<&[u8]>>, String> {
    image::ImageReader::new(std::io::Cursor::new(bytes))
        .with_guessed_format()
        .map_err(|error| error.to_string())
}

fn decode_artwork(bytes: &[u8]) -> Result<(Vec<u8>, Option<Vec<u8>>, String), String> {
    if bytes.is_empty() || bytes.len() > MAX_SOURCE_BYTES {
        return Err("Artwork data size is invalid".into());
    }
    let (width, height) = image_reader(bytes)?
        .into_dimensions()
        .map_err(|error| error.to_string())?;
    if u64::from(width).saturating_mul(u64::from(height)) > MAX_IMAGE_PIXELS {
        return Err("Artwork dimensions are too large".into());
    }
    let resized = image_reader(bytes)?
        .decode()
        .map_err(|error| error.to_string())?
        .resize_exact(128, 128, image::imageops::FilterType::Lanczos3)
        .to_rgb8();
    let (texture, accent) =
        texture_from_pixels(resized.as_raw(), 3).ok_or("Unable to convert artwork pixels")?;
    let mut preview = std::io::Cursor::new(Vec::new());
    resized
        .write_to(&mut preview, image::ImageFormat::Png)
        .map_err(|error| error.to_string())?;
    Ok((texture, Some(preview.into_inner()), accent))
}

#[cfg(any(target_os = "macos", target_os = "windows"))]
async fn prepare(url: &str) -> Result<(Vec<u8>, Option<Vec<u8>>, String), String> {
    use futures_util::StreamExt;
    use std::time::Duration;

    let parsed = url::Url::parse(url).map_err(|error| error.to_string())?;
    let bytes = match parsed.scheme() {
        "file" => {
            let path = parsed
                .to_file_path()
                .map_err(|_| "Invalid artwork file URL")?;
            let metadata = tokio::fs::metadata(&path)
                .await
                .map_err(|error| error.to_string())?;
            if metadata.len() > MAX_SOURCE_BYTES as u64 {
                return Err("Artwork file too large".into());
            }
            tokio::fs::read(path)
                .await
                .map_err(|error| error.to_string())?
        }
        "http" | "https" if parsed.username().is_empty() && parsed.password().is_none() => {
            let client = reqwest::Client::builder()
                .timeout(Duration::from_secs(7))
                .redirect(reqwest::redirect::Policy::limited(5))
                .build()
                .map_err(|error| error.to_string())?;
            let response = client
                .get(parsed)
                .send()
                .await
                .map_err(|error| error.to_string())?
                .error_for_status()
                .map_err(|error| error.to_string())?;
            if response
                .content_length()
                .is_some_and(|length| length > MAX_SOURCE_BYTES as u64)
            {
                return Err("Artwork download too large".into());
            }
            let mut stream = response.bytes_stream();
            let mut bytes = Vec::new();
            while let Some(chunk) = stream.next().await {
                let chunk = chunk.map_err(|error| error.to_string())?;
                if bytes.len().saturating_add(chunk.len()) > MAX_SOURCE_BYTES {
                    return Err("Artwork download too large".into());
                }
                bytes.extend_from_slice(&chunk);
            }
            bytes
        }
        _ => return Err("Unsupported artwork URL".into()),
    };
    prepare_bytes(&bytes).await
}

#[cfg(any(target_os = "macos", target_os = "windows"))]
async fn prepare_bytes(bytes: &[u8]) -> Result<(Vec<u8>, Option<Vec<u8>>, String), String> {
    if bytes.is_empty() || bytes.len() > MAX_SOURCE_BYTES {
        return Err("Artwork data size is invalid".into());
    }
    let bytes = bytes.to_vec();
    tokio::task::spawn_blocking(move || decode_artwork(&bytes))
        .await
        .map_err(|error| error.to_string())?
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

    #[cfg(any(target_os = "macos", target_os = "windows"))]
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

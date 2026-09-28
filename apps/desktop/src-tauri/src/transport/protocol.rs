use serde_json::Value;
use tokio::io::{AsyncRead, AsyncReadExt, AsyncWrite, AsyncWriteExt};

pub const MAX_MESSAGE: usize = 65_536;

pub async fn read<R: AsyncRead + Unpin>(reader: &mut R) -> Result<Value, String> {
    let mut header = [0_u8; 4];
    reader
        .read_exact(&mut header)
        .await
        .map_err(|e| e.to_string())?;
    let length = u32::from_be_bytes(header) as usize;
    if length == 0 || length > MAX_MESSAGE {
        return Err("Invalid 3DS frame length".into());
    }
    let mut payload = vec![0_u8; length];
    reader
        .read_exact(&mut payload)
        .await
        .map_err(|e| e.to_string())?;
    let value: Value = serde_json::from_slice(&payload).map_err(|e| e.to_string())?;
    if !value.is_object() {
        return Err("3DS message must be a JSON object".into());
    }
    Ok(value)
}

pub async fn write<W: AsyncWrite + Unpin>(writer: &mut W, value: &Value) -> Result<(), String> {
    if !value.is_object() {
        return Err("3DS message must be a JSON object".into());
    }
    let payload = serde_json::to_vec(value).map_err(|e| e.to_string())?;
    if payload.is_empty() || payload.len() > MAX_MESSAGE {
        return Err("3DS frame too large".into());
    }
    writer
        .write_all(&(payload.len() as u32).to_be_bytes())
        .await
        .map_err(|e| e.to_string())?;
    writer.write_all(&payload).await.map_err(|e| e.to_string())
}

pub async fn write_binary<W: AsyncWrite + Unpin>(
    writer: &mut W,
    payload: &[u8],
) -> Result<(), String> {
    if payload.is_empty() || payload.len() > MAX_MESSAGE {
        return Err("3DS binary frame too large".into());
    }
    writer
        .write_all(&(payload.len() as u32).to_be_bytes())
        .await
        .map_err(|e| e.to_string())?;
    writer.write_all(payload).await.map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[tokio::test]
    async fn fragmented_frame_round_trip() {
        let (mut sender, mut receiver) = tokio::io::duplex(128);
        let expected = json!({"type":"ping","id":42});
        let bytes = serde_json::to_vec(&expected).unwrap();
        let mut frame = (bytes.len() as u32).to_be_bytes().to_vec();
        frame.extend(bytes);
        let task = tokio::spawn(async move {
            for part in frame.chunks(3) {
                sender.write_all(part).await.unwrap();
            }
        });
        assert_eq!(read(&mut receiver).await.unwrap(), expected);
        task.await.unwrap();
        let (mut sender, mut receiver) = tokio::io::duplex(128);
        write(&mut sender, &expected).await.unwrap();
        assert_eq!(read(&mut receiver).await.unwrap(), expected);
    }

    #[tokio::test]
    async fn rejects_oversized_before_body() {
        let (mut sender, mut receiver) = tokio::io::duplex(16);
        sender
            .write_all(&((MAX_MESSAGE + 1) as u32).to_be_bytes())
            .await
            .unwrap();
        assert!(read(&mut receiver).await.unwrap_err().contains("length"));
    }

    #[tokio::test]
    async fn rejects_non_object() {
        let (mut sender, mut receiver) = tokio::io::duplex(16);
        sender.write_all(&3_u32.to_be_bytes()).await.unwrap();
        sender.write_all(b"[1]").await.unwrap();
        assert!(read(&mut receiver).await.unwrap_err().contains("object"));
    }

    #[tokio::test]
    async fn writes_artwork_as_binary_length_prefixed_frame() {
        let (mut sender, mut receiver) = tokio::io::duplex(64);
        write_binary(&mut sender, b"ART0payload").await.unwrap();
        let mut header = [0_u8; 4];
        receiver.read_exact(&mut header).await.unwrap();
        assert_eq!(u32::from_be_bytes(header), 11);
        let mut body = [0_u8; 11];
        receiver.read_exact(&mut body).await.unwrap();
        assert_eq!(&body, b"ART0payload");
    }
}

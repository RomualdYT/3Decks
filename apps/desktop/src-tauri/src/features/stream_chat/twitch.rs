use super::{model::text, storage::Credentials};
use reqwest::{Client, Response};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::time::Duration;

const ID: &str = "https://id.twitch.tv/oauth2";
const API: &str = "https://api.twitch.tv/helix";
const SCOPE: &str = "user:read:chat";

#[derive(Deserialize)]
pub struct DeviceGrant {
    pub device_code: String,
    pub user_code: String,
    pub verification_uri: String,
    pub expires_in: u64,
    pub interval: u64,
}

#[derive(Clone, Serialize)]
pub struct Authorization {
    pub code: String,
    pub url: String,
    pub expires_in: u64,
}

#[derive(Deserialize)]
struct Token {
    access_token: String,
    refresh_token: String,
}

#[derive(Deserialize)]
pub struct Identity {
    pub user_id: String,
    pub login: String,
    client_id: String,
    scopes: Vec<String>,
}

pub fn client() -> Client {
    let _ = rustls::crypto::ring::default_provider().install_default();
    Client::builder()
        .timeout(Duration::from_secs(10))
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .expect("Twitch HTTP client")
}

async fn response(response: Response) -> Result<Value, String> {
    let status = response.status();
    if status == 401 {
        return Err("authorization_required".into());
    }
    if status == 429 {
        return Err("rate_limited".into());
    }
    if !status.is_success() {
        return Err("twitch_unavailable".into());
    }
    response
        .json()
        .await
        .map_err(|_| "invalid_twitch_response".into())
}

pub async fn device(client: &Client, id: &str) -> Result<DeviceGrant, String> {
    let raw = response(
        client
            .post(format!("{ID}/device"))
            .form(&[("client_id", id), ("scopes", SCOPE)])
            .send()
            .await
            .map_err(|_| "twitch_unavailable")?,
    )
    .await?;
    let grant: DeviceGrant = serde_json::from_value(raw).map_err(|_| "invalid_twitch_response")?;
    let url = url::Url::parse(&grant.verification_uri).map_err(|_| "invalid_twitch_response")?;
    if url.scheme() != "https"
        || url.host_str() != Some("www.twitch.tv")
        || url.path() != "/activate"
        || url.port().is_some()
        || !url.username().is_empty()
        || url.password().is_some()
    {
        return Err("invalid_twitch_response".into());
    }
    Ok(grant)
}

pub async fn poll(client: &Client, id: &str, code: &str) -> Result<Option<Credentials>, String> {
    let response = client
        .post(format!("{ID}/token"))
        .form(&[
            ("client_id", id),
            ("device_code", code),
            ("scopes", SCOPE),
            ("grant_type", "urn:ietf:params:oauth:grant-type:device_code"),
        ])
        .send()
        .await
        .map_err(|_| "twitch_unavailable")?;
    let success = response.status().is_success();
    let raw: Value = response
        .json()
        .await
        .map_err(|_| "invalid_twitch_response")?;
    if !success {
        let reason = raw["error"]
            .as_str()
            .or_else(|| raw["message"].as_str())
            .unwrap_or("");
        return match reason {
            "authorization_pending" => Ok(None),
            "slow_down" => Err("slow_down".into()),
            "access_denied" => Err("authorization_denied".into()),
            "expired_token" | "invalid device code" => Err("authorization_expired".into()),
            _ => Err("twitch_unavailable".into()),
        };
    }
    let token: Token = serde_json::from_value(raw).map_err(|_| "invalid_twitch_response")?;
    Ok(Some(Credentials {
        client_id: id.into(),
        login: String::new(),
        access_token: token.access_token,
        refresh_token: token.refresh_token,
    }))
}

pub async fn validate(client: &Client, credentials: &Credentials) -> Result<Identity, String> {
    let raw = response(
        client
            .get(format!("{ID}/validate"))
            .header(
                "Authorization",
                format!("OAuth {}", credentials.access_token),
            )
            .send()
            .await
            .map_err(|_| "twitch_unavailable")?,
    )
    .await?;
    let identity: Identity = serde_json::from_value(raw).map_err(|_| "invalid_twitch_response")?;
    if identity.client_id != credentials.client_id
        || !identity.scopes.iter().any(|scope| scope == SCOPE)
    {
        return Err("authorization_required".into());
    }
    Ok(identity)
}

pub async fn refresh(client: &Client, credentials: &Credentials) -> Result<Credentials, String> {
    let reply = client
        .post(format!("{ID}/token"))
        .form(&[
            ("grant_type", "refresh_token"),
            ("client_id", credentials.client_id.as_str()),
            ("refresh_token", credentials.refresh_token.as_str()),
        ])
        .send()
        .await
        .map_err(|_| "twitch_unavailable")?;
    if matches!(reply.status().as_u16(), 400 | 401 | 403) {
        return Err("authorization_required".into());
    }
    let raw = response(reply).await?;
    let token: Token = serde_json::from_value(raw).map_err(|_| "authorization_required")?;
    Ok(Credentials {
        client_id: credentials.client_id.clone(),
        login: credentials.login.clone(),
        access_token: token.access_token,
        refresh_token: token.refresh_token,
    })
}

pub async fn channel(
    client: &Client,
    credentials: &Credentials,
    login: &str,
) -> Result<String, String> {
    let raw = response(
        client
            .get(format!("{API}/users"))
            .query(&[("login", login)])
            .bearer_auth(&credentials.access_token)
            .header("Client-Id", &credentials.client_id)
            .send()
            .await
            .map_err(|_| "twitch_unavailable")?,
    )
    .await?;
    raw["data"][0]["id"]
        .as_str()
        .map(str::to_owned)
        .ok_or_else(|| "channel_not_found".into())
}

pub async fn subscribe(
    client: &Client,
    credentials: &Credentials,
    channel: &str,
    user: &str,
    session: &str,
) -> Result<(), String> {
    for kind in [
        "channel.chat.message",
        "channel.chat.message_delete",
        "channel.chat.clear",
        "channel.chat.clear_user_messages",
    ] {
        let result = client.post(format!("{API}/eventsub/subscriptions"))
            .bearer_auth(&credentials.access_token).header("Client-Id", &credentials.client_id)
            .json(&json!({ "type":kind, "version":"1", "condition":{"broadcaster_user_id":channel,"user_id":user},
                "transport":{"method":"websocket","session_id":session} }))
            .send().await.map_err(|_| "twitch_unavailable")?;
        if result.status() == 403 {
            return Err("authorization_required".into());
        }
        response(result).await?;
    }
    Ok(())
}

pub fn author_color(raw: &str) -> String {
    if raw.len() == 7 && raw.starts_with('#') && raw[1..].bytes().all(|c| c.is_ascii_hexdigit()) {
        // Lift dark Twitch user colors for legibility on the console's dark surface.
        let component = |start| {
            u8::from_str_radix(&raw[start..start + 2], 16)
                .unwrap_or(180)
                .max(128)
        };
        format!(
            "#{:02x}{:02x}{:02x}",
            component(1),
            component(3),
            component(5)
        )
    } else {
        "#bda4ff".into()
    }
}

pub fn timestamp(raw: &str) -> String {
    text(raw.get(11..16).unwrap_or(""), 5)
}

/// Badge metadata needs no additional scopes beyond the existing user token.
pub async fn badge_catalog(
    client: &Client,
    credentials: &Credentials,
    channel: Option<&str>,
) -> Result<Value, String> {
    let path = if channel.is_some() {
        "chat/badges"
    } else {
        "chat/badges/global"
    };
    let mut request = client
        .get(format!("{API}/{path}"))
        .timeout(Duration::from_secs(3))
        .bearer_auth(&credentials.access_token)
        .header("Client-Id", &credentials.client_id);
    if let Some(channel) = channel {
        request = request.query(&[("broadcaster_id", channel)]);
    }
    response(request.send().await.map_err(|_| "twitch_unavailable")?).await
}

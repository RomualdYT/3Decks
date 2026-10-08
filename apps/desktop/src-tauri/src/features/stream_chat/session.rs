use super::{
    Service,
    model::{Message, Settings, text},
    storage::Credentials,
    twitch,
};
use futures_util::{SinkExt, StreamExt};
use serde_json::Value;
use std::{collections::VecDeque, time::Duration};
use tokio::time::{Instant, timeout};
use tokio_tungstenite::tungstenite::{self, protocol::WebSocketConfig};

fn reconnect_url(raw: &str) -> Result<(), String> {
    let url = url::Url::parse(raw).map_err(|_| "invalid_twitch_response")?;
    if url.scheme() != "wss"
        || url.host_str() != Some("eventsub.wss.twitch.tv")
        || url.path() != "/ws"
        || url.port().is_some()
        || !url.username().is_empty()
        || url.password().is_some()
    {
        return Err("invalid_twitch_response".into());
    }
    Ok(())
}

pub async fn run(
    service: &Service,
    settings: &Settings,
    credentials: &Credentials,
    identity: &twitch::Identity,
) -> Result<(), String> {
    let expired = |error: String| {
        if error == "authorization_required" {
            "token_expired".into()
        } else {
            error
        }
    };
    let channel = twitch::channel(&service.http, credentials, &settings.channel)
        .await
        .map_err(expired)?;
    let badges = super::badges::Catalog::load(&service.http, credentials, &channel).await;
    let config = WebSocketConfig::default()
        .max_message_size(Some(64 * 1024))
        .max_frame_size(Some(64 * 1024));
    let (mut socket, _) = timeout(
        Duration::from_secs(10),
        tokio_tungstenite::connect_async_with_config(
            "wss://eventsub.wss.twitch.tv/ws",
            Some(config),
            false,
        ),
    )
    .await
    .map_err(|_| "twitch_unavailable")?
    .map_err(|_| "twitch_unavailable")?;
    let mut keepalive = Duration::from_secs(10);
    let mut seen = VecDeque::<String>::new();
    let mut validation = Instant::now() + Duration::from_secs(3600);
    let mut resumed = false;
    loop {
        let frame = tokio::select! {
            frame = timeout(keepalive + Duration::from_secs(10), socket.next()) =>
                frame.map_err(|_| "reconnecting")?.ok_or("reconnecting")?.map_err(|_| "reconnecting")?,
            _ = tokio::time::sleep_until(validation) => {
                twitch::validate(&service.http, credentials).await.map_err(|error| if error == "authorization_required" { "token_expired".into() } else { error })?;
                validation = Instant::now() + Duration::from_secs(3600);
                continue;
            }
        };
        let raw = match frame {
            tungstenite::Message::Text(raw) => raw,
            tungstenite::Message::Ping(raw) => {
                socket
                    .send(tungstenite::Message::Pong(raw))
                    .await
                    .map_err(|_| "reconnecting")?;
                continue;
            }
            tungstenite::Message::Close(_) => return Err("reconnecting".into()),
            _ => continue,
        };
        let value: Value = serde_json::from_str(&raw).map_err(|_| "invalid_twitch_response")?;
        match value["metadata"]["message_type"].as_str().unwrap_or("") {
            "session_welcome" => {
                keepalive = Duration::from_secs(
                    value["payload"]["session"]["keepalive_timeout_seconds"]
                        .as_u64()
                        .unwrap_or(10)
                        .clamp(5, 600),
                );
                if !resumed {
                    let id = value["payload"]["session"]["id"]
                        .as_str()
                        .ok_or("invalid_twitch_response")?;
                    twitch::subscribe(&service.http, credentials, &channel, &identity.user_id, id)
                        .await
                        .map_err(expired)?;
                }
                service.set_status("connected");
            }
            "session_reconnect" => {
                let url = value["payload"]["session"]["reconnect_url"]
                    .as_str()
                    .ok_or("invalid_twitch_response")?;
                reconnect_url(url)?;
                let (new_socket, _) = timeout(
                    Duration::from_secs(10),
                    tokio_tungstenite::connect_async_with_config(url, Some(config), false),
                )
                .await
                .map_err(|_| "reconnecting")?
                .map_err(|_| "reconnecting")?;
                // Twitch transfers subscriptions; do not subscribe again on this connection.
                let _ = timeout(Duration::from_secs(2), socket.close(None)).await;
                socket = new_socket;
                resumed = true;
            }
            "revocation" => return Err("authorization_required".into()),
            "notification" => {
                let id = value["metadata"]["message_id"]
                    .as_str()
                    .ok_or("invalid_twitch_response")?;
                if seen.iter().any(|previous| previous == id) {
                    continue;
                }
                if seen.len() == 256 {
                    seen.pop_front();
                }
                seen.push_back(text(id, 128));
                let event = &value["payload"]["event"];
                let current_settings = service.settings.lock().unwrap();
                if !current_settings.enabled || current_settings.channel != settings.channel {
                    continue;
                }
                let hide_commands = current_settings.hide_commands;
                let mut snapshot = service.snapshot.write().unwrap();
                match value["metadata"]["subscription_type"]
                    .as_str()
                    .unwrap_or("")
                {
                    "channel.chat.message" => {
                        let body = text(event["message"]["text"].as_str().unwrap_or(""), 256);
                        let id = text(event["message_id"].as_str().unwrap_or(""), 64);
                        if id.is_empty()
                            || body.is_empty()
                            || (hide_commands && body.starts_with('!'))
                        {
                            continue;
                        }
                        snapshot.push(Message {
                            id,
                            user_id: text(event["chatter_user_id"].as_str().unwrap_or(""), 32),
                            author: text(event["chatter_user_name"].as_str().unwrap_or(""), 48),
                            text: body,
                            color: twitch::author_color(event["color"].as_str().unwrap_or("")),
                            time: twitch::timestamp(
                                value["metadata"]["message_timestamp"]
                                    .as_str()
                                    .unwrap_or(""),
                            ),
                            badges: badges.resolve(&event["badges"]),
                        });
                    }
                    "channel.chat.message_delete" => snapshot.messages.retain(|message| {
                        Some(message.id.as_str()) != event["message_id"].as_str()
                    }),
                    "channel.chat.clear_user_messages" => snapshot.messages.retain(|message| {
                        Some(message.user_id.as_str()) != event["target_user_id"].as_str()
                    }),
                    "channel.chat.clear" => snapshot.messages.clear(),
                    _ => {}
                }
            }
            _ => {}
        }
    }
}

use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use futures_util::{SinkExt, StreamExt};
use rand::RngCore;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::time::Duration;
use tokio::{net::TcpStream, time::timeout};
use tokio_tungstenite::{
    connect_async,
    tungstenite::{client::IntoClientRequest, http::HeaderValue, Message},
    MaybeTlsStream, WebSocketStream,
};

type Socket = WebSocketStream<MaybeTlsStream<TcpStream>>;

pub struct ObsConfig {
    host: String,
    port: u16,
    password: String,
    deadline: Duration,
}

impl ObsConfig {
    pub fn from_document(document: &Value) -> Result<Self, String> {
        let raw = &document["integrations"]["obs"];
        if raw["enabled"].as_bool() != Some(true) {
            return Err("OBS integration is disabled".into());
        }
        let host = raw["host"].as_str().unwrap_or("127.0.0.1");
        if host.is_empty()
            || host.len() > 255
            || !host
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || b".:-[]".contains(&byte))
        {
            return Err("Invalid OBS host".into());
        }
        let port = raw["port"].as_u64().unwrap_or(4455);
        if port == 0 || port > u16::MAX as u64 {
            return Err("Invalid OBS port".into());
        }
        let seconds = raw["timeout"].as_f64().unwrap_or(2.0);
        if !(0.2..=15.0).contains(&seconds) {
            return Err("Invalid OBS timeout".into());
        }
        Ok(Self {
            host: host.into(),
            port: port as u16,
            password: raw["password"].as_str().unwrap_or("").into(),
            deadline: Duration::from_secs_f64(seconds),
        })
    }

    fn url(&self) -> String {
        let host = if self.host.contains(':') && !self.host.starts_with('[') {
            format!("[{}]", self.host)
        } else {
            self.host.clone()
        };
        format!("ws://{host}:{}/", self.port)
    }
}

pub struct ObsClient {
    socket: Socket,
    deadline: Duration,
}

impl ObsClient {
    pub async fn connect(config: &ObsConfig) -> Result<Self, String> {
        let mut request = config
            .url()
            .into_client_request()
            .map_err(|e| e.to_string())?;
        request.headers_mut().insert(
            "Sec-WebSocket-Protocol",
            HeaderValue::from_static("obswebsocket.json"),
        );
        let (socket, response) = timeout(config.deadline, connect_async(request))
            .await
            .map_err(|_| "OBS connection timed out".to_string())?
            .map_err(|e| format!("OBS connection failed: {e}"))?;
        if response
            .headers()
            .get("Sec-WebSocket-Protocol")
            .and_then(|value| value.to_str().ok())
            != Some("obswebsocket.json")
        {
            return Err("OBS did not select the JSON WebSocket protocol".into());
        }
        let mut client = Self {
            socket,
            deadline: config.deadline,
        };
        let hello = client.receive().await?;
        if hello["op"].as_u64() != Some(0) {
            return Err("OBS did not send Hello".into());
        }
        let mut identify = json!({"rpcVersion":hello["d"]["rpcVersion"].as_u64().unwrap_or(1),"eventSubscriptions":0});
        if let Some(auth) = hello["d"]["authentication"].as_object() {
            if config.password.is_empty() {
                return Err("OBS requires a WebSocket password".into());
            }
            let salt = auth
                .get("salt")
                .and_then(Value::as_str)
                .ok_or("Invalid OBS authentication salt")?;
            let challenge = auth
                .get("challenge")
                .and_then(Value::as_str)
                .ok_or("Invalid OBS authentication challenge")?;
            identify["authentication"] = json!(authentication(&config.password, salt, challenge));
        }
        client.send(&json!({"op":1,"d":identify})).await?;
        if client.receive().await?["op"].as_u64() != Some(2) {
            return Err("OBS rejected identification".into());
        }
        Ok(client)
    }

    async fn send(&mut self, value: &Value) -> Result<(), String> {
        let text = serde_json::to_string(value).map_err(|e| e.to_string())?;
        timeout(self.deadline, self.socket.send(Message::Text(text.into())))
            .await
            .map_err(|_| "OBS send timed out".to_string())?
            .map_err(|e| e.to_string())
    }

    async fn receive(&mut self) -> Result<Value, String> {
        for _ in 0..16 {
            let frame = timeout(self.deadline, self.socket.next())
                .await
                .map_err(|_| "OBS response timed out".to_string())?
                .ok_or("OBS closed the connection")?
                .map_err(|e| e.to_string())?;
            if let Message::Text(text) = frame {
                let value: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
                if value.is_object() {
                    return Ok(value);
                }
                return Err("OBS returned invalid JSON".into());
            }
        }
        Err("OBS sent too many non-JSON frames".into())
    }

    pub async fn request(&mut self, kind: &str, data: Value) -> Result<Value, String> {
        let id = format!("{:016x}", rand::rngs::OsRng.next_u64());
        self.send(&json!({"op":6,"d":{"requestType":kind,"requestId":id,"requestData":data}}))
            .await?;
        for _ in 0..16 {
            let response = self.receive().await?;
            if response["op"].as_u64() != Some(7)
                || response["d"]["requestId"].as_str() != Some(id.as_str())
            {
                continue;
            }
            if response["d"]["requestStatus"]["result"].as_bool() != Some(true) {
                let comment = response["d"]["requestStatus"]["comment"]
                    .as_str()
                    .unwrap_or("request refused");
                return Err(format!("OBS {kind}: {comment}"));
            }
            return Ok(response["d"]["responseData"]
                .as_object()
                .map(|_| response["d"]["responseData"].clone())
                .unwrap_or_else(|| json!({})));
        }
        Err("OBS did not answer the request".into())
    }
}

fn authentication(password: &str, salt: &str, challenge: &str) -> String {
    let secret = BASE64.encode(Sha256::digest(format!("{password}{salt}").as_bytes()));
    BASE64.encode(Sha256::digest(format!("{secret}{challenge}").as_bytes()))
}

pub async fn perform(config: &ObsConfig, action: &Value) -> Result<&'static str, String> {
    let kind = action
        .as_str()
        .or_else(|| action["type"].as_str())
        .ok_or("OBS action type missing")?;
    let mut client = ObsClient::connect(config).await?;
    match kind {
        "obs.scene.set" => {
            client
                .request(
                    "SetCurrentProgramScene",
                    json!({"sceneName":required(action,"scene")?}),
                )
                .await?;
            Ok("OBS scene changed")
        }
        "obs.record.toggle" => {
            client.request("ToggleRecord", json!({})).await?;
            Ok("OBS recording toggled")
        }
        "obs.stream.toggle" => {
            client.request("ToggleStream", json!({})).await?;
            Ok("OBS stream toggled")
        }
        "obs.source.toggle" => {
            let scene = required(action, "scene")?;
            let source = required(action, "source")?;
            let found = client
                .request(
                    "GetSceneItemId",
                    json!({"sceneName":scene,"sourceName":source}),
                )
                .await?;
            let id = found["sceneItemId"]
                .as_i64()
                .ok_or("OBS did not return a scene item ID")?;
            let current = client
                .request(
                    "GetSceneItemEnabled",
                    json!({"sceneName":scene,"sceneItemId":id}),
                )
                .await?;
            let enabled = current["sceneItemEnabled"]
                .as_bool()
                .ok_or("OBS did not return source state")?;
            client
                .request(
                    "SetSceneItemEnabled",
                    json!({"sceneName":scene,"sceneItemId":id,"sceneItemEnabled":!enabled}),
                )
                .await?;
            Ok("OBS source toggled")
        }
        _ => Err("Unknown OBS action".into()),
    }
}

pub async fn status(config: &ObsConfig) -> Result<Value, String> {
    let mut client = ObsClient::connect(config).await?;
    let version = client.request("GetVersion", json!({})).await?;
    let scenes = client.request("GetSceneList", json!({})).await?;
    Ok(
        json!({"connected":true,"obs_version":version["obsVersion"],"websocket_version":version["obsWebSocketVersion"],
        "scenes":scenes["scenes"].as_array().map(|items| items.iter().filter_map(|item| item["sceneName"].as_str()).collect::<Vec<_>>()).unwrap_or_default(),
        "current_scene":scenes["currentProgramSceneName"]}),
    )
}

fn required<'a>(action: &'a Value, name: &str) -> Result<&'a str, String> {
    let value = action[name]
        .as_str()
        .ok_or_else(|| format!("OBS {name} is required"))?;
    if value.is_empty() || value.len() > 256 {
        return Err(format!("Invalid OBS {name}"));
    }
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::{net::TcpListener, time::Duration};
    use tokio_tungstenite::accept_hdr_async;
    #[test]
    fn rejects_disabled_or_invalid_hosts() {
        let mut document =
            json!({"integrations":{"obs":{"enabled":false,"host":"localhost","port":4455}}});
        assert!(ObsConfig::from_document(&document).is_err());
        document["integrations"]["obs"]["enabled"] = json!(true);
        document["integrations"]["obs"]["host"] = json!("evil/path");
        assert!(ObsConfig::from_document(&document).is_err());
    }
    #[test]
    fn obs_authentication_matches_reference_vector() {
        assert_eq!(
            authentication(
                "supersecretpassword",
                "lM1GncleQOaCu9lT1yeUZhFYnqhsLLP1G5lAGo3ixaI=",
                "+IxH4CnCiqpX1rM9scsNynZzbOe4KhDeYcTNS3PDaeY="
            ),
            "1Ct943GAT+6YQUUX47Ia/ncufilbe6+oD6lY+5kaCu4="
        );
    }

    #[tokio::test]
    #[ignore = "requires a local TCP listener"]
    async fn authenticated_scene_change_round_trip() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        let server = tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            let mut websocket = accept_hdr_async(stream, |request: &tokio_tungstenite::tungstenite::handshake::server::Request, mut response: tokio_tungstenite::tungstenite::handshake::server::Response| {
                assert_eq!(request.headers().get("Sec-WebSocket-Protocol").unwrap(), "obswebsocket.json");
                response.headers_mut().insert("Sec-WebSocket-Protocol", HeaderValue::from_static("obswebsocket.json"));
                Ok(response)
            }).await.unwrap();
            let salt = "lM1GncleQOaCu9lT1yeUZhFYnqhsLLP1G5lAGo3ixaI=";
            let challenge = "+IxH4CnCiqpX1rM9scsNynZzbOe4KhDeYcTNS3PDaeY=";
            websocket.send(Message::Text(json!({"op":0,"d":{"rpcVersion":1,"authentication":{"salt":salt,"challenge":challenge}}}).to_string().into())).await.unwrap();
            let identify: Value =
                serde_json::from_str(websocket.next().await.unwrap().unwrap().to_text().unwrap())
                    .unwrap();
            assert_eq!(identify["op"], 1);
            assert_eq!(
                identify["d"]["authentication"],
                authentication("test-password", salt, challenge)
            );
            websocket
                .send(Message::Text(
                    json!({"op":2,"d":{"negotiatedRpcVersion":1}})
                        .to_string()
                        .into(),
                ))
                .await
                .unwrap();
            let request: Value =
                serde_json::from_str(websocket.next().await.unwrap().unwrap().to_text().unwrap())
                    .unwrap();
            assert_eq!(request["d"]["requestType"], "SetCurrentProgramScene");
            assert_eq!(request["d"]["requestData"]["sceneName"], "Direct");
            websocket.send(Message::Text(json!({"op":7,"d":{"requestId":request["d"]["requestId"],"requestStatus":{"result":true,"code":100},"responseData":{}}}).to_string().into())).await.unwrap();
        });
        let document = json!({"integrations":{"obs":{"enabled":true,"host":"127.0.0.1","port":port,"password":"test-password","timeout":2.0}}});
        let config = ObsConfig::from_document(&document).unwrap();
        let action = json!({"type":"obs.scene.set","scene":"Direct"});
        assert_eq!(
            timeout(Duration::from_secs(5), perform(&config, &action))
                .await
                .unwrap()
                .unwrap(),
            "OBS scene changed"
        );
        server.await.unwrap();
    }
}

use crate::app::state::Shared;
use serde_json::{Value, json};
use std::{sync::Arc, time::Duration};

/// Coalesce busy chats into at most four complete history patches per second.
/// Chat delivery stays independent of slow telemetry/media polling.
pub async fn run(shared: Arc<Shared>) {
    let mut stop = shared.stop.subscribe();
    let mut tick = tokio::time::interval(Duration::from_millis(250));
    tick.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
    let mut previous = Value::Null;
    loop {
        tokio::select! {
            _ = stop.changed() => break,
            _ = tick.tick() => {
                if *stop.borrow() { break; }
                let snapshot = json!(shared.stream_chat.snapshot());
                if snapshot != previous {
                    shared.latest_state.write().unwrap()["stream_chat"] = snapshot.clone();
                    let _ = shared.chat_updates.send(json!({"type":"state.update", "stream_chat":snapshot}));
                    previous = snapshot;
                }
            }
        }
    }
}

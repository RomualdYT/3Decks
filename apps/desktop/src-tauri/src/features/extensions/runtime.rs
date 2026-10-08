//! One task owns each extension process; no process I/O holds the host lock.
use super::{Worker, now, validate_snapshot};
use serde_json::{Value, json};
use std::sync::{Arc, RwLock};
use std::time::Duration;
use tokio::sync::{mpsc, oneshot};
use tokio::task::JoinHandle;

#[derive(Clone)]
pub(super) struct View {
    pub status: String,
    pub error: String,
    pub snapshot: Value,
    pub updated_at: f64,
}

type Reply = oneshot::Sender<Result<Value, String>>;
enum Command {
    Action {
        params: Value,
        reply: Reply,
    },
    #[cfg(test)]
    Poll {
        reply: Reply,
    },
}

pub struct ActionRequest {
    commands: mpsc::Sender<Command>,
    params: Value,
}

impl ActionRequest {
    pub async fn run(self) -> Result<String, String> {
        let (reply, response) = oneshot::channel();
        self.commands
            .try_send(Command::Action {
                params: self.params,
                reply,
            })
            .map_err(|_| "Extension unavailable or command queue full")?;
        let result = response.await.map_err(|_| "Extension stopped")??;
        let ok = result["ok"].as_bool() == Some(true);
        let message = result["message"].as_str().unwrap_or(if ok {
            "Extension action complete"
        } else {
            "Extension action failed"
        });
        let message = message.chars().take(63).collect();
        if ok { Ok(message) } else { Err(message) }
    }
}

pub(super) struct Runtime {
    commands: mpsc::Sender<Command>,
    view: Arc<RwLock<View>>,
    task: JoinHandle<()>,
    stop: Option<oneshot::Sender<()>>,
}

impl Runtime {
    pub fn spawn(mut worker: Worker, manifest: Value, initialize: Value) -> Self {
        let (commands, mut receiver) = mpsc::channel::<Command>(16);
        let view = Arc::new(RwLock::new(View {
            status: "starting".into(),
            error: String::new(),
            snapshot: json!({}),
            updated_at: 0.0,
        }));
        let published = view.clone();
        let (stop, stopped) = oneshot::channel();
        let task = tokio::spawn(async move {
            {
                let run = async {
                    let result = worker.call("initialize", initialize).await;
                    let initialized = result.and_then(|result| {
                        if result["api_version"] == 1 {
                            Ok(())
                        } else {
                            Err("Extension returned incompatible API version".into())
                        }
                    });
                    if let Err(error) = initialized {
                        fail(&published, error);
                        return;
                    }
                    published.write().unwrap().status = "ready".into();
                    let delay =
                        Duration::from_secs_f64(manifest["poll_interval"].as_f64().unwrap_or(2.0));
                    let mut tick = tokio::time::interval(delay);
                    tick.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
                    loop {
                        let command = tokio::select! {
                            command = receiver.recv() => match command { Some(command) => command, None => break },
                            _ = tick.tick() => {
                                if let Err(error) = poll(&mut worker, &manifest, &published).await {
                                    fail(&published, error);
                                    break;
                                }
                                continue;
                            }
                        };
                        match command {
                            #[cfg(test)]
                            Command::Poll { reply } => {
                                let result = poll(&mut worker, &manifest, &published).await;
                                let error = result.as_ref().err().cloned();
                                let _ = reply.send(result);
                                tick.reset();
                                if let Some(error) = error {
                                    fail(&published, error);
                                    break;
                                }
                            }
                            Command::Action { params, reply } => {
                                let result = worker.call("action", params).await;
                                let error = result.as_ref().err().cloned();
                                let succeeded =
                                    result.as_ref().is_ok_and(|result| result["ok"] == true);
                                let _ = reply.send(result);
                                if let Some(error) = error {
                                    fail(&published, error);
                                    break;
                                }
                                if succeeded {
                                    tick.reset_immediately();
                                }
                            }
                        }
                    }
                };
                tokio::select! {
                    _ = run => {},
                    _ = stopped => {},
                }
            }
            let _ = worker.child.kill().await;
        });
        Self {
            commands,
            view,
            task,
            stop: Some(stop),
        }
    }

    pub async fn stop(mut self) {
        if let Some(stop) = self.stop.take() {
            let _ = stop.send(());
        }
        // The task cancels I/O, terminates the process and closes pending replies.
        let _ = (&mut self.task).await;
    }

    pub fn status(&self) -> String {
        self.view.read().unwrap().status.clone()
    }
    pub fn view(&self) -> View {
        self.view.read().unwrap().clone()
    }
    pub fn action(&self, params: Value) -> ActionRequest {
        ActionRequest {
            commands: self.commands.clone(),
            params,
        }
    }
    #[cfg(test)]
    pub async fn poll(&self) -> Result<Value, String> {
        let (reply, response) = oneshot::channel();
        self.commands
            .try_send(Command::Poll { reply })
            .map_err(|_| "Extension stopped")?;
        response.await.map_err(|_| "Extension stopped".to_owned())?
    }
}

impl Drop for Runtime {
    fn drop(&mut self) {
        self.task.abort();
    }
}

fn fail(view: &RwLock<View>, error: String) {
    let mut view = view.write().unwrap();
    view.status = "error".into();
    view.error = error;
    view.snapshot = json!({});
}

async fn poll(worker: &mut Worker, manifest: &Value, view: &RwLock<View>) -> Result<Value, String> {
    let snapshot = worker.call("poll", json!({})).await?;
    validate_snapshot(manifest, &snapshot)?;
    let mut view = view.write().unwrap();
    view.snapshot = snapshot.clone();
    view.updated_at = now();
    Ok(snapshot)
}

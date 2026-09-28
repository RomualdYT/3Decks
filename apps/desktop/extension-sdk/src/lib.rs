//! Author-facing API for out-of-process 3Decks extensions.
//! Protocol v1 is JSON Lines on stdin/stdout; diagnostics belong on stderr.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    io::{self, BufRead, BufReader, BufWriter, Read, Write},
    path::PathBuf,
};

pub const API_VERSION: u64 = 1;
const MAX_MESSAGE: usize = 64 * 1024;

#[derive(Clone, Debug, Deserialize)]
pub struct Context {
    pub extension_id: String,
    pub settings: Value,
    pub data_dir: PathBuf,
    pub platform: String,
}

#[derive(Clone, Debug, Serialize, Default)]
pub struct Snapshot {
    pub states: BTreeMap<String, bool>,
    pub sources: BTreeMap<String, Value>,
    pub dashboards: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Serialize)]
pub struct ActionResult {
    pub ok: bool,
    pub message: String,
}

impl ActionResult {
    pub fn success(message: impl Into<String>) -> Self {
        Self {
            ok: true,
            message: message.into(),
        }
    }

    pub fn failure(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            message: message.into(),
        }
    }
}

pub trait Extension {
    fn initialize(&mut self, _context: &Context) -> Result<(), String> {
        Ok(())
    }
    fn poll(&mut self, _context: &Context) -> Result<Snapshot, String> {
        Ok(Snapshot::default())
    }
    fn action(
        &mut self,
        context: &Context,
        id: &str,
        arguments: &Value,
    ) -> Result<ActionResult, String>;
    fn shutdown(&mut self, _context: &Context) -> Result<(), String> {
        Ok(())
    }
}

pub struct Session<E: Extension> {
    extension: E,
    context: Option<Context>,
}

impl<E: Extension> Session<E> {
    pub fn new(extension: E) -> Self {
        Self {
            extension,
            context: None,
        }
    }

    /// Dispatch one protocol request. This is also useful for unit tests.
    pub fn dispatch(&mut self, request: Value) -> Value {
        let id = request.get("id").and_then(Value::as_u64).unwrap_or(0);
        let result = self.dispatch_inner(&request);
        match result {
            Ok(value) => json!({"id": id, "result": value, "error": null}),
            Err(message) => {
                json!({"id": id, "result": null, "error": message.chars().take(200).collect::<String>()})
            }
        }
    }

    fn dispatch_inner(&mut self, request: &Value) -> Result<Value, String> {
        let method = request["method"].as_str().ok_or("Method missing")?;
        let params = &request["params"];
        if method == "initialize" {
            if self.context.is_some() {
                return Err("Already initialized".into());
            }
            if params["api_version"] != API_VERSION {
                return Err("Unsupported API version".into());
            }
            let context: Context =
                serde_json::from_value(params.clone()).map_err(|e| e.to_string())?;
            self.extension.initialize(&context)?;
            self.context = Some(context);
            return Ok(json!({"api_version": API_VERSION}));
        }
        let context = self.context.as_ref().ok_or("Initialize first")?;
        match method {
            "poll" => {
                serde_json::to_value(self.extension.poll(context)?).map_err(|e| e.to_string())
            }
            "action" => {
                let action = params["action"].as_str().ok_or("Action ID missing")?;
                let args = params.get("arguments").unwrap_or(&Value::Null);
                serde_json::to_value(self.extension.action(context, action, args)?)
                    .map_err(|e| e.to_string())
            }
            "shutdown" => {
                self.extension.shutdown(context)?;
                self.context = None;
                Ok(json!({}))
            }
            _ => Err("Unknown method".into()),
        }
    }
}

pub fn serve<E: Extension>(extension: E) -> io::Result<()> {
    let stdin = io::stdin();
    let stdout = io::stdout();
    serve_io(
        extension,
        BufReader::new(stdin.lock()),
        BufWriter::new(stdout.lock()),
    )
}

pub fn serve_io<E: Extension, R: BufRead, W: Write>(
    extension: E,
    mut input: R,
    mut output: W,
) -> io::Result<()> {
    let mut session = Session::new(extension);
    while let Some(line) = read_bounded_line(&mut input)? {
        let response = match serde_json::from_slice::<Value>(&line) {
            Ok(request) => session.dispatch(request),
            Err(_) => json!({"id":0,"result":null,"error":"Invalid JSON"}),
        };
        let mut bytes = serde_json::to_vec(&response).map_err(io::Error::other)?;
        if bytes.len() > MAX_MESSAGE {
            bytes = serde_json::to_vec(&json!({
                "id": response["id"], "result": null, "error": "Response exceeds 64 KiB"
            }))
            .map_err(io::Error::other)?;
        }
        bytes.push(b'\n');
        output.write_all(&bytes)?;
        output.flush()?;
    }
    Ok(())
}

fn read_bounded_line<R: Read>(reader: &mut R) -> io::Result<Option<Vec<u8>>> {
    let mut line = Vec::new();
    let mut byte = [0u8; 1];
    loop {
        match reader.read(&mut byte)? {
            0 if line.is_empty() => return Ok(None),
            0 => {
                return Err(io::Error::new(
                    io::ErrorKind::UnexpectedEof,
                    "Incomplete request",
                ))
            }
            _ if byte[0] == b'\n' => return Ok(Some(line)),
            _ => {
                if line.len() >= MAX_MESSAGE {
                    return Err(io::Error::new(
                        io::ErrorKind::InvalidData,
                        "Request exceeds 64 KiB",
                    ));
                }
                line.push(byte[0]);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Counter(u32);
    impl Extension for Counter {
        fn poll(&mut self, _: &Context) -> Result<Snapshot, String> {
            let mut snapshot = Snapshot::default();
            snapshot.states.insert("ready".into(), true);
            Ok(snapshot)
        }
        fn action(&mut self, _: &Context, id: &str, _: &Value) -> Result<ActionResult, String> {
            if id != "increment" {
                return Err("Unknown action".into());
            }
            self.0 += 1;
            Ok(ActionResult::success(format!("Count: {}", self.0)))
        }
    }
    #[test]
    fn dispatches_native_protocol() {
        let mut session = Session::new(Counter(0));
        assert!(session.dispatch(json!({"id":1,"method":"poll","params":{}}))["error"].is_string());
        assert_eq!(session.dispatch(json!({"id":2,"method":"initialize","params":{"api_version":1,"extension_id":"example","settings":{},"data_dir":"/tmp","platform":"darwin"}}))["result"]["api_version"], 1);
        assert_eq!(
            session.dispatch(
                json!({"id":3,"method":"action","params":{"action":"increment","arguments":{}}})
            )["result"]["message"],
            "Count: 1"
        );
        assert_eq!(
            session.dispatch(json!({"id":4,"method":"poll","params":{}}))["result"]["states"]
                ["ready"],
            true
        );
    }
    #[test]
    fn serializes_json_lines() {
        let input = b"{\"id\":1,\"method\":\"initialize\",\"params\":{\"api_version\":1,\"extension_id\":\"x\",\"settings\":{},\"data_dir\":\"/tmp\",\"platform\":\"linux\"}}\n{\"id\":2,\"method\":\"action\",\"params\":{\"action\":\"increment\",\"arguments\":{}}}\n";
        let mut output = Vec::new();
        serve_io(Counter(0), BufReader::new(&input[..]), &mut output).unwrap();
        let replies: Vec<Value> = output
            .split(|byte| *byte == b'\n')
            .filter(|line| !line.is_empty())
            .map(|line| serde_json::from_slice(line).unwrap())
            .collect();
        assert_eq!(replies.len(), 2);
        assert_eq!(replies[1]["result"]["message"], "Count: 1");
    }
}

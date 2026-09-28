use serde_json::Value;
use three_decks_extension_sdk::{serve, ActionResult, Context, Extension, Snapshot};

#[derive(Default)]
struct Counter(u32);

impl Extension for Counter {
    fn poll(&mut self, _: &Context) -> Result<Snapshot, String> {
        let mut snapshot = Snapshot::default();
        snapshot.states.insert("ready".into(), true);
        Ok(snapshot)
    }

    fn action(&mut self, _: &Context, id: &str, _: &Value) -> Result<ActionResult, String> {
        match id {
            "increment" => {
                self.0 += 1;
                Ok(ActionResult::success(format!("Compteur : {}", self.0)))
            }
            _ => Err("Action inconnue".into()),
        }
    }
}

fn main() -> std::io::Result<()> {
    serve(Counter::default())
}

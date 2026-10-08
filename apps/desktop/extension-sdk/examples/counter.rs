use serde_json::{json, Value};
use three_decks_extension_sdk::{serve, ActionResult, Context, Extension, Snapshot};

#[derive(Default)]
struct Counter(u32);

impl Extension for Counter {
    fn poll(&mut self, _: &Context) -> Result<Snapshot, String> {
        let mut snapshot = Snapshot::default();
        snapshot.states.insert("ready".into(), true);
        snapshot.dashboards.insert("overview".into(), json!({
            "title": {"en": "Counter", "fr": "Compteur"},
            "cards": [{
                "label": {"en": "Button presses", "fr": "Appuis sur le bouton"},
                "value": self.0.to_string(),
                "detail": {"en": "Press Increment to add one", "fr": "Appuyez sur Incrémenter pour ajouter un"}
            }]
        }));
        Ok(snapshot)
    }

    fn action(&mut self, _: &Context, id: &str, _: &Value) -> Result<ActionResult, String> {
        match id {
            "increment" => {
                self.0 = self.0.saturating_add(1);
                Ok(ActionResult::success(format!("Counter / Compteur: {}", self.0)))
            }
            _ => Err("Action inconnue".into()),
        }
    }
}

fn main() -> std::io::Result<()> {
    serve(Counter::default())
}

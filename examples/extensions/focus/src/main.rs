mod config;
mod presentation;
mod storage;
mod timer;

use serde_json::Value;
use std::time::{SystemTime, UNIX_EPOCH};
use three_decks_extension_sdk::{ActionResult, Context, Extension, Snapshot, serve};

use config::Settings;
use storage::Storage;
use timer::{Phase, Status, Timer};

struct Focus {
    settings: Settings,
    timer: Timer,
    storage: Option<Storage>,
}

impl Default for Focus {
    fn default() -> Self {
        let settings = Settings::default();
        Self {
            timer: Timer::new(&settings),
            settings,
            storage: None,
        }
    }
}

impl Focus {
    /// Commit only after the durable save succeeds. A failed write must not
    /// acknowledge an action or award the same completed session twice.
    fn commit(&mut self, timer: Timer) -> Result<(), String> {
        self.storage
            .as_ref()
            .ok_or("Focus is not initialized")?
            .save(&timer)?;
        self.timer = timer;
        Ok(())
    }

    fn advance(&mut self, now_ms: u64) -> Result<(), String> {
        let mut timer = self.timer.clone();
        if timer.advance(now_ms, &self.settings) {
            self.commit(timer)
        } else {
            self.timer = timer;
            Ok(())
        }
    }
}

impl Extension for Focus {
    fn initialize(&mut self, context: &Context) -> Result<(), String> {
        self.settings = Settings::parse(&context.settings)?;
        let storage = Storage::new(context.data_dir.clone());
        let mut timer = storage
            .load()?
            .unwrap_or_else(|| Timer::new(&self.settings));
        timer.cycle_sessions = timer.cycle_sessions.min(self.settings.sessions_per_cycle);
        // New settings apply to the next phase. An existing paused/running
        // timer retains its original duration so it never jumps unexpectedly.
        if timer.status == Status::Ready {
            timer.reset(&self.settings);
        }
        timer.advance(now_ms()?, &self.settings);
        storage.save(&timer)?;
        self.timer = timer;
        self.storage = Some(storage);
        Ok(())
    }

    fn poll(&mut self, _: &Context) -> Result<Snapshot, String> {
        let now = now_ms()?;
        self.advance(now)?;
        Ok(presentation::snapshot(&self.timer, &self.settings, now))
    }

    fn action(&mut self, _: &Context, id: &str, arguments: &Value) -> Result<ActionResult, String> {
        if !arguments
            .as_object()
            .is_some_and(|arguments| arguments.is_empty())
        {
            return Err("Focus actions do not take arguments".into());
        }
        let now = now_ms()?;
        self.advance(now)?;
        let mut timer = self.timer.clone();
        let message = match id {
            "toggle" => {
                timer.toggle(now);
                match timer.status {
                    Status::Running => "Timer started / Minuteur lancé",
                    _ => "Timer paused / Minuteur en pause",
                }
            }
            "reset" => {
                timer.reset(&self.settings);
                "Timer reset / Minuteur réinitialisé"
            }
            "skip" => {
                timer.skip(&self.settings);
                "Next phase ready / Phase suivante prête"
            }
            "work" | "short_break" | "long_break" => {
                let phase = match id {
                    "work" => Phase::Work,
                    "short_break" => Phase::ShortBreak,
                    _ => Phase::LongBreak,
                };
                if timer.phase == phase {
                    return Ok(ActionResult::success(
                        "Timer already selected / Minuteur déjà choisi",
                    ));
                }
                if timer.status == Status::Running {
                    return Ok(ActionResult::failure(
                        "Pause first / Suspendez d'abord le minuteur",
                    ));
                }
                timer.select(phase, &self.settings);
                "Timer ready / Minuteur prêt"
            }
            _ => return Err("Unknown Focus action".into()),
        };
        self.commit(timer)?;
        Ok(ActionResult::success(message))
    }
}

fn now_ms() -> Result<u64, String> {
    let elapsed = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| e.to_string())?;
    u64::try_from(elapsed.as_millis()).map_err(|e| e.to_string())
}

fn main() -> std::io::Result<()> {
    serve(Focus::default())
}

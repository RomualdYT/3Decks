use serde_json::{Value, json};
use three_decks_extension_sdk::Snapshot;

use crate::{
    config::Settings,
    timer::{Phase, Status, Timer},
};

const GREEN: &str = "#66CB10";
const BLUE: &str = "#29A3FF";
const TEAL: &str = "#14B8A6";
const PURPLE: &str = "#A78BFA";
const MUTED: &str = "#94A3B8";

fn text(en: impl Into<String>, fr: impl Into<String>) -> Value {
    json!({"en": en.into(), "fr": fr.into()})
}

fn phase_name(phase: Phase) -> Value {
    match phase {
        Phase::Work => text("Focus", "Concentration"),
        Phase::ShortBreak => text("Short break", "Pause courte"),
        Phase::LongBreak => text("Long break", "Pause longue"),
    }
}

fn button(id: &str, label: Value, detail: Value, icon: &str, color: &str, active: bool) -> Value {
    json!({
        "id": id, "label": label, "detail": detail, "icon": icon,
        "color": color, "active": active, "action": {"id": id, "arguments": {}}
    })
}

pub fn snapshot(timer: &Timer, settings: &Settings, now_ms: u64) -> Snapshot {
    let running = timer.status == Status::Running;
    let (toggle_label, toggle_detail, toggle_icon) = match timer.status {
        Status::Ready => (
            text("Start", "Démarrer"),
            text("Start this timer", "Lancer le minuteur"),
            "play",
        ),
        Status::Running => (
            text("Pause", "Suspendre"),
            text("Keep your remaining time", "Conserver le temps restant"),
            "pause",
        ),
        Status::Paused => (
            text("Resume", "Reprendre"),
            text("Continue where you left off", "Continuer la session"),
            "play",
        ),
    };
    let duration = |phase: Phase| {
        let minutes = phase.duration_ms(settings) / 60_000;
        text(format!("{minutes} min"), format!("{minutes} min"))
    };
    let controls = json!([
        button(
            "toggle",
            toggle_label,
            toggle_detail,
            toggle_icon,
            GREEN,
            running
        ),
        button(
            "reset",
            text("Reset", "Repartir"),
            text(
                "Reset timer; keep your stats",
                "Repartir sans effacer les statistiques"
            ),
            "previous",
            MUTED,
            false
        ),
        button(
            "skip",
            text("Skip", "Passer"),
            text(
                "Next phase; no session credited",
                "Phase suivante sans compter de session"
            ),
            "next",
            MUTED,
            false
        ),
        button(
            "work",
            text("Focus", "Travail"),
            duration(Phase::Work),
            "star",
            BLUE,
            timer.phase == Phase::Work
        ),
        button(
            "short_break",
            text("Short break", "Pause courte"),
            duration(Phase::ShortBreak),
            "pause",
            TEAL,
            timer.phase == Phase::ShortBreak
        ),
        button(
            "long_break",
            text("Long break", "Pause longue"),
            duration(Phase::LongBreak),
            "power",
            PURPLE,
            timer.phase == Phase::LongBreak
        )
    ]);

    let today = timer.today(now_ms);
    let sessions = today.map_or(0, |day| day.sessions);
    let minutes = today.map_or(0, |day| day.focus_ms / 60_000);
    let next = timer.next_phase(settings);
    let remaining_seconds = timer.remaining_ms.div_ceil(1_000);
    let remaining = format!(
        "{:02}:{:02}",
        remaining_seconds / 60,
        remaining_seconds % 60
    );
    let status = match timer.status {
        Status::Ready => text("Ready when you are", "À votre rythme"),
        Status::Running => text("One thing at a time", "Une chose à la fois"),
        Status::Paused => text("Paused · take your time", "En pause · à votre rythme"),
    };
    let next_minutes = next.duration_ms(settings) / 60_000;
    let cycle_position = timer.cycle_sessions.min(settings.sessions_per_cycle);
    let panel = json!({
        "title": text("Focus · your rhythm", "Focus · votre rythme"),
        "status": "ok",
        "cards": [
            {
                "label": phase_name(timer.phase), "value": remaining, "detail": status,
                "progress": 100.0 * (1.0 - timer.remaining_ms as f64 / timer.duration_ms as f64)
            },
            {
                "label": text("Today's sessions", "Sessions du jour"),
                "value": format!("{sessions} / {}", settings.daily_goal),
                "detail": if sessions >= settings.daily_goal {
                    text("Daily goal reached", "Objectif atteint")
                } else { text("Small steps, steady progress", "Un pas après l'autre") },
                "progress": (f64::from(sessions) * 100.0 / f64::from(settings.daily_goal)).min(100.0)
            },
            {
                "label": text("Focused today", "Concentration du jour"),
                "value": if minutes >= 60 { format!("{}h {:02}m", minutes / 60, minutes % 60) } else { format!("{minutes} min") },
                "detail": text("Completed sessions only", "Sessions terminées")
            },
            {
                "label": phase_name(next), "value": format!("{next_minutes} min"),
                "detail": text(
                    format!("Next · cycle {cycle_position} / {}", settings.sessions_per_cycle),
                    format!("Ensuite · cycle {cycle_position} / {}", settings.sessions_per_cycle)
                )
            }
        ]
    });

    let mut snapshot = Snapshot::default();
    // Action IDs also serve as state keys for individually configured buttons.
    snapshot.states.insert("toggle".into(), running);
    snapshot
        .states
        .insert("work".into(), timer.phase == Phase::Work);
    snapshot
        .states
        .insert("short_break".into(), timer.phase == Phase::ShortBreak);
    snapshot
        .states
        .insert("long_break".into(), timer.phase == Phase::LongBreak);
    snapshot.states.insert("running".into(), running);
    snapshot
        .states
        .insert("paused".into(), timer.status == Status::Paused);
    snapshot
        .states
        .insert("break".into(), timer.phase != Phase::Work);
    snapshot
        .states
        .insert("goal_reached".into(), sessions >= settings.daily_goal);
    snapshot.sources.insert("controls".into(), controls);
    snapshot.dashboards.insert("overview".into(), panel);
    snapshot
}

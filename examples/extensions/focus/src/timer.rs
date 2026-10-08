use chrono::{Local, TimeZone};
use serde::{Deserialize, Serialize};

use crate::config::Settings;

const MAX_DURATION_MS: u64 = 120 * 60 * 1_000;
const HISTORY_DAYS: usize = 30;

#[derive(Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    Work,
    ShortBreak,
    LongBreak,
}

impl Phase {
    pub fn duration_ms(self, settings: &Settings) -> u64 {
        u64::from(match self {
            Self::Work => settings.work_minutes,
            Self::ShortBreak => settings.short_break_minutes,
            Self::LongBreak => settings.long_break_minutes,
        }) * 60_000
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Ready,
    Running,
    Paused,
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Day {
    pub date: String,
    pub sessions: u32,
    pub focus_ms: u64,
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Timer {
    pub phase: Phase,
    pub status: Status,
    pub duration_ms: u64,
    pub remaining_ms: u64,
    pub deadline_ms: Option<u64>,
    pub cycle_sessions: u32,
    pub total_sessions: u64,
    pub history: Vec<Day>,
}

impl Timer {
    pub fn new(settings: &Settings) -> Self {
        let duration_ms = Phase::Work.duration_ms(settings);
        Self {
            phase: Phase::Work,
            status: Status::Ready,
            duration_ms,
            remaining_ms: duration_ms,
            deadline_ms: None,
            cycle_sessions: 0,
            total_sessions: 0,
            history: Vec::new(),
        }
    }

    pub fn validate(&self) -> Result<(), String> {
        if !(60_000..=MAX_DURATION_MS).contains(&self.duration_ms)
            || self.remaining_ms > self.duration_ms
            || self.remaining_ms == 0
            || (self.status == Status::Running) != self.deadline_ms.is_some()
            || self
                .deadline_ms
                .is_some_and(|deadline| deadline > i64::MAX as u64)
            || (self.status == Status::Ready && self.remaining_ms != self.duration_ms)
            || self.cycle_sessions > 12
            || self.history.len() > HISTORY_DAYS
        {
            return Err("Invalid saved Focus timer".into());
        }
        for (index, day) in self.history.iter().enumerate() {
            if chrono::NaiveDate::parse_from_str(&day.date, "%Y-%m-%d").is_err()
                || day.focus_ms > u64::from(day.sessions) * MAX_DURATION_MS
                || self.history[..index]
                    .iter()
                    .any(|previous| previous.date >= day.date)
            {
                return Err("Invalid saved Focus history".into());
            }
        }
        Ok(())
    }

    pub fn next_phase(&self, settings: &Settings) -> Phase {
        match self.phase {
            Phase::Work if self.cycle_sessions.saturating_add(1) >= settings.sessions_per_cycle => {
                Phase::LongBreak
            }
            Phase::Work => Phase::ShortBreak,
            Phase::ShortBreak | Phase::LongBreak => Phase::Work,
        }
    }

    /// Absolute deadlines survive process restarts and computer sleep. Only the
    /// phase that was actually started may complete; downtime never fabricates
    /// multiple work sessions, even when automatic transitions are enabled.
    /// Returns true when a transition or clock correction needs a durable save.
    pub fn advance(&mut self, now_ms: u64, settings: &Settings) -> bool {
        let Some(saved_deadline) = self.deadline_ms else {
            return false;
        };
        // Moving the system clock backwards must not freeze the countdown for
        // hours or increase the remaining time beyond the last displayed value.
        let deadline = saved_deadline.min(now_ms.saturating_add(self.remaining_ms));
        self.deadline_ms = Some(deadline);
        self.remaining_ms = self.remaining_ms.min(deadline.saturating_sub(now_ms));
        if self.remaining_ms > 0 {
            return deadline != saved_deadline;
        }
        let completed_phase = self.phase;
        let next_phase = self.next_phase(settings);
        if completed_phase == Phase::Work {
            self.record_session(deadline);
            self.cycle_sessions = self
                .cycle_sessions
                .saturating_add(1)
                .min(settings.sessions_per_cycle);
        }
        self.select(next_phase, settings);
        if match next_phase {
            Phase::Work => settings.auto_start_work,
            _ => settings.auto_start_breaks,
        } {
            self.start(now_ms);
        }
        true
    }

    pub fn toggle(&mut self, now_ms: u64) {
        if self.status == Status::Running {
            self.status = Status::Paused;
            self.deadline_ms = None;
        } else {
            self.start(now_ms);
        }
    }

    pub fn reset(&mut self, settings: &Settings) {
        self.select(self.phase, settings);
    }

    /// Skipping a phase never awards a completed session or starts another one.
    pub fn skip(&mut self, settings: &Settings) {
        let next = match self.phase {
            Phase::Work if self.cycle_sessions >= settings.sessions_per_cycle => Phase::LongBreak,
            Phase::Work => Phase::ShortBreak,
            _ => Phase::Work,
        };
        self.select(next, settings);
    }

    pub fn select(&mut self, phase: Phase, settings: &Settings) {
        if self.phase == Phase::LongBreak && phase != Phase::LongBreak {
            self.cycle_sessions = 0;
        }
        self.phase = phase;
        self.status = Status::Ready;
        self.duration_ms = phase.duration_ms(settings);
        self.remaining_ms = self.duration_ms;
        self.deadline_ms = None;
    }

    pub fn today(&self, now_ms: u64) -> Option<&Day> {
        let date = local_date(now_ms);
        self.history.iter().find(|day| day.date == date)
    }

    fn start(&mut self, now_ms: u64) {
        self.status = Status::Running;
        self.deadline_ms = Some(now_ms.saturating_add(self.remaining_ms));
    }

    fn record_session(&mut self, completed_at_ms: u64) {
        self.total_sessions = self.total_sessions.saturating_add(1);
        let date = local_date(completed_at_ms);
        let index = match self.history.binary_search_by(|day| day.date.cmp(&date)) {
            Ok(index) => index,
            Err(index) => {
                self.history.insert(
                    index,
                    Day {
                        date,
                        sessions: 0,
                        focus_ms: 0,
                    },
                );
                index
            }
        };
        let day = &mut self.history[index];
        day.sessions = day.sessions.saturating_add(1);
        day.focus_ms = day.focus_ms.saturating_add(self.duration_ms);
        if self.history.len() > HISTORY_DAYS {
            self.history.remove(0);
        }
    }
}

pub fn local_date(timestamp_ms: u64) -> String {
    Local
        .timestamp_millis_opt(timestamp_ms.min(i64::MAX as u64) as i64)
        .single()
        .map(|date| date.format("%Y-%m-%d").to_string())
        .unwrap_or_else(|| Local::now().format("%Y-%m-%d").to_string())
}

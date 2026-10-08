use serde::Deserialize;
use serde_json::Value;

#[derive(Clone, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Settings {
    pub work_minutes: u32,
    pub short_break_minutes: u32,
    pub long_break_minutes: u32,
    pub sessions_per_cycle: u32,
    pub daily_goal: u32,
    pub auto_start_breaks: bool,
    pub auto_start_work: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            work_minutes: 25,
            short_break_minutes: 5,
            long_break_minutes: 15,
            sessions_per_cycle: 4,
            daily_goal: 4,
            auto_start_breaks: false,
            auto_start_work: false,
        }
    }
}

impl Settings {
    pub fn parse(value: &Value) -> Result<Self, String> {
        let settings: Self = serde_json::from_value(value.clone()).map_err(|e| e.to_string())?;
        if !(1..=120).contains(&settings.work_minutes)
            || !(1..=60).contains(&settings.short_break_minutes)
            || !(1..=120).contains(&settings.long_break_minutes)
            || !(1..=12).contains(&settings.sessions_per_cycle)
            || !(1..=24).contains(&settings.daily_goal)
        {
            return Err("Focus settings are outside their supported ranges".into());
        }
        Ok(settings)
    }
}

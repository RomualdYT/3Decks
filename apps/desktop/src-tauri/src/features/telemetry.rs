use serde_json::{json, Value};
use std::{
    sync::{Arc, Mutex},
    time::Instant,
};
use sysinfo::{Disks, Networks, System};

pub struct Telemetry {
    system: System,
    disks: Disks,
    networks: Networks,
    previous: Instant,
}

impl Telemetry {
    pub fn new() -> Self {
        let mut system = System::new();
        system.refresh_cpu_usage();
        Self {
            system,
            disks: Disks::new_with_refreshed_list(),
            networks: Networks::new_with_refreshed_list(),
            previous: Instant::now(),
        }
    }

    fn sample(&mut self) -> Value {
        self.system.refresh_cpu_usage();
        self.system.refresh_memory();
        self.disks.refresh(false);
        self.networks.refresh(false);
        let now = Instant::now();
        let seconds = now.duration_since(self.previous).as_secs_f64();
        self.previous = now;

        let total_memory = self.system.total_memory();
        let used_memory = self.system.used_memory().min(total_memory);
        let disk = self
            .disks
            .iter()
            .find(|disk| disk.mount_point().to_str() == Some("/"))
            .or_else(|| self.disks.iter().max_by_key(|disk| disk.total_space()));
        let (disk_total, disk_free) = disk
            .map(|disk| (disk.total_space(), disk.available_space()))
            .unwrap_or((0, 0));
        let received: u64 = self.networks.iter().map(|(_, data)| data.received()).sum();
        let transmitted: u64 = self
            .networks
            .iter()
            .map(|(_, data)| data.transmitted())
            .sum();

        let mut state = json!({
            "cpu": percentage(self.system.global_cpu_usage() as f64),
            "memory": ratio(used_memory, total_memory),
            "memory_used_mb": to_mb(used_memory),
            "memory_total_mb": to_mb(total_memory),
            "disk": ratio(disk_total.saturating_sub(disk_free), disk_total),
            "disk_free_mb": to_mb(disk_free),
            "disk_total_mb": to_mb(disk_total),
        });
        if seconds >= 0.2 {
            state["network_down_kbps"] = json!(((received as f64 * 8.0 / seconds / 1000.0).round()
                as u64)
                .min(u32::MAX as u64));
            state["network_up_kbps"] = json!(
                ((transmitted as f64 * 8.0 / seconds / 1000.0).round() as u64).min(u32::MAX as u64)
            );
        }
        state
    }
}

fn percentage(value: f64) -> u8 {
    value.round().clamp(0.0, 100.0) as u8
}
fn ratio(used: u64, total: u64) -> u8 {
    if total == 0 {
        0
    } else {
        percentage(used as f64 * 100.0 / total as f64)
    }
}
fn to_mb(bytes: u64) -> u64 {
    bytes / 1_048_576
}

pub async fn sample(telemetry: Arc<Mutex<Telemetry>>) -> Value {
    tokio::task::spawn_blocking(move || telemetry.lock().unwrap().sample())
        .await
        .unwrap_or_else(|_| json!({}))
}

pub fn merge(state: &mut Value, metrics: Value) {
    if let (Some(state), Some(metrics)) = (state.as_object_mut(), metrics.as_object()) {
        state.extend(metrics.clone());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn ratios_are_bounded() {
        assert_eq!(ratio(1, 0), 0);
        assert_eq!(ratio(50, 100), 50);
        assert_eq!(ratio(200, 100), 100);
        assert_eq!(to_mb(1_048_576), 1);
    }
}

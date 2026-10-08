//! Installed application names and launch identifiers from the Windows Start menu.
use serde::Deserialize;
use std::{sync::OnceLock, time::{Duration, Instant}};
use tokio::{process::Command, sync::Mutex};

#[derive(Clone, Deserialize)]
struct InstalledApp {
    #[serde(rename = "Name")]
    name: String,
    #[serde(rename = "AppID")]
    id: String,
}

type AppCache = Option<(Instant, Vec<InstalledApp>)>;
static CACHE: OnceLock<Mutex<AppCache>> = OnceLock::new();

async fn installed() -> Vec<InstalledApp> {
    let mut cache = CACHE.get_or_init(|| Mutex::new(None)).lock().await;
    if let Some((time, apps)) = cache.as_ref() {
        if time.elapsed() < Duration::from_secs(60) {
            return apps.clone();
        }
    }
    // Constant script: application names are never interpolated into PowerShell.
    let script = "$OutputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); ConvertTo-Json -Compress -InputObject @(Get-StartApps | Select-Object Name,AppID)";
    let powershell = std::path::PathBuf::from(std::env::var_os("SystemRoot").unwrap_or_else(|| "C:\\Windows".into()))
        .join("System32/WindowsPowerShell/v1.0/powershell.exe");
    let output = tokio::time::timeout(Duration::from_secs(8), Command::new(powershell)
        .args(["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script])
        .creation_flags(windows::Win32::System::Threading::CREATE_NO_WINDOW.0)
        .kill_on_drop(true)
        .output()).await;
    let apps = match output {
        Ok(Ok(output)) if output.status.success() => serde_json::from_slice::<Vec<InstalledApp>>(&output.stdout).ok(),
        _ => None,
    };
    let apps: Vec<InstalledApp> = match apps {
        Some(apps) => apps.into_iter().filter(|app| !app.name.is_empty() && !app.id.is_empty()).collect(),
        None => {
            crate::app::logging::append("Windows installed app discovery unavailable; manual executable paths remain available");
            cache.as_ref().map(|(_, apps)| apps.clone()).unwrap_or_default()
        }
    };
    *cache = Some((Instant::now(), apps.clone()));
    apps
}

pub async fn names() -> Vec<String> {
    installed().await.into_iter().map(|app| app.name).collect()
}

fn resolve(apps: &[InstalledApp], target: &str) -> String {
    apps.iter().find(|app| app.name.eq_ignore_ascii_case(target))
        .map(|app| format!("shell:AppsFolder\\{}", app.id))
        .unwrap_or_else(|| target.to_owned())
}

pub async fn launch_target(target: &str) -> String {
    // Explicit paths, executables and protocols do not need discovery.
    if target.contains(['\\', '/', ':']) || target.ends_with(".exe") || target.ends_with(".lnk") {
        return target.to_owned();
    }
    resolve(&installed().await, target)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolves_installed_names_without_restricting_custom_targets() {
        let apps = vec![InstalledApp { name: "Une application".into(), id: "Vendor.Package!App".into() }];
        assert_eq!(resolve(&apps, "UNE APPLICATION"), "shell:AppsFolder\\Vendor.Package!App");
        assert_eq!(resolve(&apps, "C:\\Mes apps\\outil.exe"), "C:\\Mes apps\\outil.exe");
        assert_eq!(resolve(&apps, "outil.exe"), "outil.exe");
    }
}

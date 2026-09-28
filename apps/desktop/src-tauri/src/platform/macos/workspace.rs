//! AppKit adapter for opening web links and local files with the user's
//! default application. The call runs off the Tokio reactor thread.

use objc2_app_kit::NSWorkspace;
use objc2_foundation::{NSString, NSURL};

pub async fn open_web_url(url: &str) -> Result<(), String> {
    let url = url.to_owned();
    tokio::task::spawn_blocking(move || {
        let text = NSString::from_str(&url);
        let value = NSURL::URLWithString(&text).ok_or("Invalid URL")?;
        if NSWorkspace::sharedWorkspace().openURL(&value) {
            Ok(())
        } else {
            Err("NSWorkspace could not open the URL".into())
        }
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn open_file(path: &str) -> Result<(), String> {
    let path = path.to_owned();
    tokio::task::spawn_blocking(move || {
        let text = NSString::from_str(&path);
        let value = NSURL::fileURLWithPath(&text);
        if NSWorkspace::sharedWorkspace().openURL(&value) {
            Ok(())
        } else {
            Err("NSWorkspace could not open the file".into())
        }
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn launch_app(target: &str) -> Result<(), String> {
    let target = target.to_owned();
    tokio::task::spawn_blocking(move || {
        let workspace = NSWorkspace::sharedWorkspace();
        let name = NSString::from_str(&target);
        let url = if target.ends_with(".app") || target.starts_with('/') {
            NSURL::fileURLWithPath(&name)
        } else if let Some(url) = workspace.URLForApplicationWithBundleIdentifier(&name) {
            url
        } else {
            // AppKit still exposes name lookup for user configured app names.
            #[allow(deprecated)]
            let path = workspace
                .fullPathForApplication(&name)
                .ok_or_else(|| format!("Application not found: {target}"))?;
            NSURL::fileURLWithPath(&path)
        };
        if workspace.openURL(&url) {
            Ok(())
        } else {
            Err(format!("Could not launch application: {target}"))
        }
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn quit_app(target: &str) -> Result<(), String> {
    let target = target.to_owned();
    tokio::task::spawn_blocking(move || {
        let workspace = NSWorkspace::sharedWorkspace();
        let mut found = false;
        for app in workspace.runningApplications().iter() {
            let matches = app
                .localizedName()
                .is_some_and(|name| name.to_string().eq_ignore_ascii_case(&target))
                || app
                    .bundleIdentifier()
                    .is_some_and(|id| id.to_string().eq_ignore_ascii_case(&target))
                || app
                    .bundleURL()
                    .is_some_and(|url| url.path().is_some_and(|path| path.to_string() == target));
            if matches {
                found = true;
                if !app.terminate() {
                    return Err(format!("Application refused to quit: {target}"));
                }
            }
        }
        if found {
            Ok(())
        } else {
            Err(format!("Application is not running: {target}"))
        }
    })
    .await
    .map_err(|error| error.to_string())?
}

//! Discover launchable application bundles without opening them.
use std::{fs, path::PathBuf};

pub async fn names() -> Vec<String> {
    tokio::task::spawn_blocking(|| {
        let mut directories = vec![
            PathBuf::from("/Applications"),
            PathBuf::from("/Applications/Utilities"),
            PathBuf::from("/System/Applications"),
            PathBuf::from("/System/Applications/Utilities"),
        ];
        if let Some(home) = std::env::var_os("HOME") {
            directories.push(PathBuf::from(home).join("Applications"));
        }
        let mut names = Vec::new();
        for directory in directories {
            let Ok(entries) = fs::read_dir(directory) else {
                continue;
            };
            for entry in entries.flatten().take(4096) {
                let path = entry.path();
                if path.extension().is_some_and(|extension| extension == "app")
                    && path.join("Contents/Info.plist").is_file()
                    && let Some(name) = path.file_stem().and_then(|name| name.to_str())
                {
                    names.push(name.to_owned());
                }
            }
        }
        names.sort_by_key(|name| name.to_lowercase());
        names.dedup();
        names
    })
    .await
    .unwrap_or_default()
}

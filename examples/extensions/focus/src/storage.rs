use serde::{Deserialize, Serialize};
use std::{fs, io::Write, path::PathBuf};

use crate::timer::Timer;

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Document {
    version: u32,
    timer: Timer,
}

pub struct Storage {
    directory: PathBuf,
}

impl Storage {
    pub fn new(directory: PathBuf) -> Self {
        Self { directory }
    }

    pub fn load(&self) -> Result<Option<Timer>, String> {
        let path = self.directory.join("focus.json");
        let metadata = match fs::metadata(&path) {
            Ok(metadata) => metadata,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(error) => return Err(format!("Cannot read Focus data: {error}")),
        };
        if metadata.len() > 64 * 1024 {
            return Err("Saved Focus data exceeds 64 KiB".into());
        }
        let document: Document =
            serde_json::from_slice(&fs::read(path).map_err(|e| e.to_string())?)
                .map_err(|e| format!("Cannot read Focus data: {e}"))?;
        if document.version != 1 {
            return Err("Unsupported Focus save version".into());
        }
        document.timer.validate()?;
        Ok(Some(document.timer))
    }

    pub fn save(&self, timer: &Timer) -> Result<(), String> {
        fs::create_dir_all(&self.directory).map_err(|e| e.to_string())?;
        let temporary = self.directory.join("focus.json.tmp");
        let result = (|| {
            let bytes = serde_json::to_vec_pretty(&Document {
                version: 1,
                timer: timer.clone(),
            })
            .map_err(|e| e.to_string())?;
            let mut file = fs::File::create(&temporary).map_err(|e| e.to_string())?;
            file.write_all(&bytes).map_err(|e| e.to_string())?;
            file.sync_all().map_err(|e| e.to_string())?;
            drop(file);
            fs::rename(&temporary, self.directory.join("focus.json")).map_err(|e| e.to_string())
        })();
        if result.is_err() {
            let _ = fs::remove_file(temporary);
        }
        result.map_err(|error| format!("Cannot save Focus data: {error}"))
    }
}

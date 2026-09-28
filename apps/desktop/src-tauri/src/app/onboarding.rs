use serde::{Deserialize, Serialize};
use std::{fs, io::Write, path::PathBuf, sync::Mutex};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Progress {
    pub step: u8,
    pub completed: bool,
}

impl Default for Progress {
    fn default() -> Self {
        Self {
            step: 0,
            completed: false,
        }
    }
}

pub struct OnboardingStore {
    path: PathBuf,
    current: Mutex<Progress>,
}

impl OnboardingStore {
    pub fn new(path: PathBuf) -> Self {
        let current = fs::read(&path)
            .ok()
            .and_then(|bytes| serde_json::from_slice::<Progress>(&bytes).ok())
            .filter(|progress| progress.step <= 3)
            .unwrap_or_default();
        Self {
            path,
            current: Mutex::new(current),
        }
    }

    pub fn read(&self) -> Progress {
        self.current.lock().unwrap().clone()
    }

    pub fn save(&self, step: u8, completed: bool) -> Result<Progress, String> {
        if step > 3 {
            return Err("Invalid onboarding step".into());
        }
        let mut current = self.current.lock().unwrap();
        let next = Progress { step, completed };
        let bytes = serde_json::to_vec_pretty(&next).map_err(|error| error.to_string())?;
        let temporary = self
            .path
            .with_extension(format!("{}.tmp", rand::random::<u64>()));
        let mut options = fs::OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        let mut file = options
            .open(&temporary)
            .map_err(|error| error.to_string())?;
        let written = file.write_all(&bytes).and_then(|()| file.sync_all());
        drop(file);
        let result = written.and_then(|()| fs::rename(&temporary, &self.path));
        if result.is_err() {
            let _ = fs::remove_file(&temporary);
        }
        result.map_err(|error| error.to_string())?;
        *current = next.clone();
        Ok(next)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resumes_after_restart_and_rejects_invalid_steps() {
        let folder =
            std::env::temp_dir().join(format!("3decks-onboarding-{}", rand::random::<u64>()));
        fs::create_dir(&folder).unwrap();
        let path = folder.join("onboarding.json");
        let store = OnboardingStore::new(path.clone());
        assert_eq!(store.read(), Progress::default());
        store.save(2, false).unwrap();
        assert_eq!(
            OnboardingStore::new(path.clone()).read(),
            Progress {
                step: 2,
                completed: false
            }
        );
        assert!(store.save(4, false).is_err());
        assert_eq!(store.read().step, 2);
        store.save(3, true).unwrap();
        assert!(OnboardingStore::new(path).read().completed);
        fs::remove_dir_all(folder).unwrap();
    }
}

use serde_json::{json, Value};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Window {
    pub app: String,
    pub title: String,
    pub pid: i64,
    pub number: i64,
}

impl Window {
    pub fn id(&self) -> String {
        format!("window-{}-{}", self.pid, self.number)
    }

    pub fn entry(&self, active: bool) -> Value {
        let mut entry = json!({
            "id":self.id(), "label":truncate(&self.app, 24),
            "detail":truncate(&self.title, 40), "icon":"app", "color":"#64748B"
        });
        if active {
            entry["active"] = json!(true);
        }
        entry
    }
}

fn truncate(text: &str, maximum: usize) -> String {
    text.chars().take(maximum).collect()
}

#[cfg(target_os = "macos")]
mod macos {
    use super::Window;
    use std::ffi::{c_char, c_void, CString};
    use tokio::{
        process::Command,
        time::{timeout, Duration},
    };

    type Ref = *const c_void;

    #[link(name = "CoreGraphics", kind = "framework")]
    unsafe extern "C" {
        fn CGWindowListCopyWindowInfo(options: u32, relative: u32) -> Ref;
    }
    #[link(name = "CoreFoundation", kind = "framework")]
    unsafe extern "C" {
        fn CFArrayGetCount(array: Ref) -> isize;
        fn CFArrayGetValueAtIndex(array: Ref, index: isize) -> Ref;
        fn CFDictionaryGetValue(dictionary: Ref, key: Ref) -> Ref;
        fn CFStringCreateWithCString(allocator: Ref, text: *const c_char, encoding: u32) -> Ref;
        fn CFStringGetCString(value: Ref, buffer: *mut c_char, size: isize, encoding: u32) -> bool;
        fn CFNumberGetValue(value: Ref, number_type: i32, output: *mut c_void) -> bool;
        fn CFRelease(value: Ref);
    }

    const UTF8: u32 = 0x08000100;
    const SINT64: i32 = 4;
    const OPTIONS: u32 = 1 | 16;

    unsafe fn key(name: &str) -> Ref {
        let name = CString::new(name).unwrap();
        unsafe { CFStringCreateWithCString(std::ptr::null(), name.as_ptr(), UTF8) }
    }
    unsafe fn field(entry: Ref, key: Ref) -> Ref {
        unsafe { CFDictionaryGetValue(entry, key) }
    }
    unsafe fn string(value: Ref) -> String {
        if value.is_null() {
            return String::new();
        }
        let mut buffer = [0_i8; 512];
        if unsafe { CFStringGetCString(value, buffer.as_mut_ptr(), buffer.len() as isize, UTF8) } {
            let bytes: Vec<u8> = buffer
                .iter()
                .take_while(|&&byte| byte != 0)
                .map(|&byte| byte as u8)
                .collect();
            String::from_utf8_lossy(&bytes).into_owned()
        } else {
            String::new()
        }
    }
    unsafe fn number(value: Ref) -> i64 {
        if value.is_null() {
            return 0;
        }
        let mut result = 0_i64;
        if unsafe { CFNumberGetValue(value, SINT64, (&mut result as *mut i64).cast()) } {
            result
        } else {
            0
        }
    }

    fn list_sync() -> Vec<Window> {
        // CoreFoundation objects created here are released on this same thread.
        unsafe {
            let array = CGWindowListCopyWindowInfo(OPTIONS, 0);
            if array.is_null() {
                return vec![];
            }
            let keys = [
                "kCGWindowOwnerName",
                "kCGWindowName",
                "kCGWindowLayer",
                "kCGWindowOwnerPID",
                "kCGWindowNumber",
            ]
            .map(|name| key(name));
            if keys.iter().any(|key| key.is_null()) {
                for key in keys {
                    if !key.is_null() {
                        CFRelease(key);
                    }
                }
                CFRelease(array);
                return vec![];
            }
            let mut windows = Vec::new();
            for index in 0..CFArrayGetCount(array) {
                let item = CFArrayGetValueAtIndex(array, index);
                if item.is_null() || number(field(item, keys[2])) != 0 {
                    continue;
                }
                let app = string(field(item, keys[0]));
                if app.is_empty() {
                    continue;
                }
                windows.push(Window {
                    app,
                    title: string(field(item, keys[1])),
                    pid: number(field(item, keys[3])),
                    number: number(field(item, keys[4])),
                });
                if windows.len() >= 32 {
                    break;
                }
            }
            for key in keys {
                CFRelease(key);
            }
            CFRelease(array);
            windows
        }
    }

    pub async fn list() -> Vec<Window> {
        tokio::task::spawn_blocking(list_sync)
            .await
            .unwrap_or_default()
    }

    pub async fn focus(window: &Window) -> Result<&'static str, String> {
        const SCRIPT: &str = "on run argv\nset appName to item 1 of argv\nset windowName to item 2 of argv\ntell application \"System Events\"\n tell process appName\n  set frontmost to true\n  if windowName is not \"\" then\n   try\n    perform action \"AXRaise\" of first window whose name is windowName\n   end try\n  end if\n end tell\nend tell\nend run";
        let output = timeout(
            Duration::from_secs(4),
            Command::new("/usr/bin/osascript")
                .kill_on_drop(true)
                .arg("-e")
                .arg(SCRIPT)
                .arg(&window.app)
                .arg(&window.title)
                .output(),
        )
        .await
        .map_err(|_| "Window focus timed out".to_string())?
        .map_err(|e| e.to_string())?;
        if output.status.success() {
            Ok("Window focused")
        } else {
            Err(String::from_utf8_lossy(&output.stderr).trim().to_string())
        }
    }
}

#[cfg(target_os = "macos")]
pub use macos::{focus, list};

#[cfg(target_os = "windows")]
pub use super::win32::windowing::{focus, list};

#[cfg(not(any(target_os = "macos", target_os = "windows")))]
pub async fn list() -> Vec<Window> {
    vec![]
}

#[cfg(not(any(target_os = "macos", target_os = "windows")))]
pub async fn focus(_window: &Window) -> Result<&'static str, String> {
    Err("Window focus is not implemented on this platform yet".into())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn window_entry_has_stable_identity_and_bounded_text() {
        let window = Window {
            app: "A".repeat(30),
            title: "B".repeat(50),
            pid: 12,
            number: 34,
        };
        let entry = window.entry(true);
        assert_eq!(entry["id"], "window-12-34");
        assert_eq!(entry["label"].as_str().unwrap().len(), 24);
        assert_eq!(entry["detail"].as_str().unwrap().len(), 40);
    }
}

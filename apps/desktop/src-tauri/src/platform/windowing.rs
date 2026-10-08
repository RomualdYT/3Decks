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
    use objc2_app_kit::{NSApplicationActivationOptions, NSRunningApplication, NSWorkspace};
    use std::ffi::{c_char, c_void, CString};

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
        static kCFBooleanTrue: Ref;
    }
    #[link(name = "ApplicationServices", kind = "framework")]
    unsafe extern "C" {
        fn AXUIElementCreateApplication(pid: i32) -> Ref;
        fn AXUIElementCopyAttributeValue(element: Ref, attribute: Ref, value: *mut Ref) -> i32;
        fn AXUIElementPerformAction(element: Ref, action: Ref) -> i32;
        fn AXUIElementSetAttributeValue(element: Ref, attribute: Ref, value: Ref) -> i32;
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

    /// Releases a CoreFoundation object created or copied by this module.
    struct Owned(Ref);
    impl Owned {
        fn new(value: Ref) -> Option<Self> {
            (!value.is_null()).then_some(Self(value))
        }
    }
    impl Drop for Owned {
        fn drop(&mut self) {
            unsafe { CFRelease(self.0) }
        }
    }
    fn cf_key(name: &str) -> Result<Owned, String> {
        Owned::new(unsafe { key(name) }).ok_or_else(|| "CoreFoundation string unavailable".into())
    }

    /// Makes the application frontmost through Accessibility. Unlike AppKit
    /// activation, which macOS 14+ treats as a request the frontmost app must
    /// yield to, this is honoured while 3Decks runs in the background.
    unsafe fn raise_application(element: Ref) -> bool {
        let Ok(frontmost) = cf_key("AXFrontmost") else {
            return false;
        };
        unsafe { AXUIElementSetAttributeValue(element, frontmost.0, kCFBooleanTrue) == 0 }
    }

    /// Raises the window whose title matches, and makes it the main window.
    unsafe fn raise_window(element: Ref, title: &str) -> Result<(), String> {
        let windows_key = cf_key("AXWindows")?;
        let title_key = cf_key("AXTitle")?;
        let raise_key = cf_key("AXRaise")?;
        let main_key = cf_key("AXMain")?;
        let mut windows: Ref = std::ptr::null();
        let result = unsafe { AXUIElementCopyAttributeValue(element, windows_key.0, &mut windows) };
        let windows = Owned::new(windows).filter(|_| result == 0).ok_or_else(|| {
            format!("Accessibility permission or window access unavailable ({result})")
        })?;
        for index in 0..unsafe { CFArrayGetCount(windows.0) } {
            let candidate = unsafe { CFArrayGetValueAtIndex(windows.0, index) };
            let mut value: Ref = std::ptr::null();
            if unsafe { AXUIElementCopyAttributeValue(candidate, title_key.0, &mut value) } != 0 {
                continue;
            }
            let Some(value) = Owned::new(value) else {
                continue;
            };
            if unsafe { string(value.0) } != title {
                continue;
            }
            if unsafe { AXUIElementPerformAction(candidate, raise_key.0) } != 0 {
                return Err("Window could not be raised".into());
            }
            unsafe { AXUIElementSetAttributeValue(candidate, main_key.0, kCFBooleanTrue) };
            return Ok(());
        }
        Err("Window not found".into())
    }

    /// Same path as launching from the Dock: always allowed, and brings an
    /// already running application forward without choosing a window.
    fn reopen(app: &NSRunningApplication) -> bool {
        app.bundleURL()
            .is_some_and(|url| NSWorkspace::sharedWorkspace().openURL(&url))
    }

    fn focus_sync(window: Window) -> Result<&'static str, String> {
        let pid = i32::try_from(window.pid).map_err(|_| "Invalid window process ID")?;
        let app = NSRunningApplication::runningApplicationWithProcessIdentifier(pid)
            .ok_or("Application is no longer running")?;
        // Stages are tried by outcome rather than by macOS version: whether
        // activation is honoured also depends on the frontmost application.
        let mut active = app.activateWithOptions(NSApplicationActivationOptions::empty());
        let element = Owned::new(unsafe { AXUIElementCreateApplication(pid) });
        if !active {
            active = element
                .as_ref()
                .is_some_and(|element| unsafe { raise_application(element.0) });
        }
        if window.title.is_empty() {
            return if active || reopen(&app) {
                Ok("Application focused")
            } else {
                Err("Could not activate application".into())
            };
        }
        let raised = element
            .ok_or_else(|| "Accessibility element unavailable".to_string())
            .and_then(|element| unsafe { raise_window(element.0, &window.title) });
        match raised {
            Ok(()) if active || reopen(&app) => Ok("Window focused"),
            Ok(()) => Err("Could not activate application".into()),
            // The window is gone or not accessible: the application is still
            // the most useful thing to bring forward.
            Err(_) if active || reopen(&app) => Ok("Application focused"),
            Err(error) => Err(error),
        }
    }

    pub async fn focus(window: &Window) -> Result<&'static str, String> {
        let window = window.clone();
        tokio::task::spawn_blocking(move || focus_sync(window))
            .await
            .map_err(|error| error.to_string())?
    }
}

#[cfg(target_os = "macos")]
pub use macos::{focus, list};

#[cfg(target_os = "windows")]
pub use super::windows::windowing::{focus, list};

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

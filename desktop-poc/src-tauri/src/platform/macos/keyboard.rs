//! Layout-aware Quartz shortcuts. Only the validated key and modifiers cross
//! this boundary; no AppleScript or command string is constructed.
use std::ffi::c_void;

const SHIFT: u64 = 1 << 17;
const CONTROL: u64 = 1 << 18;
const OPTION: u64 = 1 << 19;
const COMMAND: u64 = 1 << 20;
const SESSION_EVENT_TAP: u32 = 1;

#[link(name = "Carbon", kind = "framework")]
unsafe extern "C" {
    static kTISPropertyUnicodeKeyLayoutData: *const c_void;
    fn TISCopyCurrentKeyboardLayoutInputSource() -> *const c_void;
    fn TISGetInputSourceProperty(source: *const c_void, key: *const c_void) -> *const c_void;
    fn UCKeyTranslate(
        layout: *const c_void,
        key_code: u16,
        action: u16,
        modifiers: u32,
        keyboard_type: u32,
        options: u32,
        dead_key_state: *mut u32,
        max_length: u32,
        actual_length: *mut u32,
        output: *mut u16,
    ) -> i32;
}

#[link(name = "CoreFoundation", kind = "framework")]
unsafe extern "C" {
    fn CFDataGetBytePtr(data: *const c_void) -> *const u8;
    fn CFRelease(value: *const c_void);
}

#[link(name = "ApplicationServices", kind = "framework")]
unsafe extern "C" {
    fn AXIsProcessTrusted() -> bool;
}

#[link(name = "CoreGraphics", kind = "framework")]
unsafe extern "C" {
    fn CGEventSourceGetKeyboardType(source: *const c_void) -> u32;
    fn CGEventCreateKeyboardEvent(
        source: *const c_void,
        key_code: u16,
        down: bool,
    ) -> *const c_void;
    fn CGEventSetFlags(event: *const c_void, flags: u64);
    fn CGEventPost(tap: u32, event: *const c_void);
}

fn key_code(character: char) -> Result<(u16, bool), String> {
    let source = unsafe { TISCopyCurrentKeyboardLayoutInputSource() };
    if source.is_null() {
        return Err("Current keyboard layout is unavailable".into());
    }
    let result = (|| {
        let data = unsafe { TISGetInputSourceProperty(source, kTISPropertyUnicodeKeyLayoutData) };
        if data.is_null() {
            return Err("Current keyboard layout has no Unicode mapping".into());
        }
        let layout = unsafe { CFDataGetBytePtr(data) };
        if layout.is_null() {
            return Err("Current keyboard layout is empty".into());
        }
        let keyboard_type = unsafe { CGEventSourceGetKeyboardType(std::ptr::null()) };
        let mut best: Option<(u16, bool)> = None;
        for code in 0..128_u16 {
            for (modifier_state, shift) in [(0, false), (2, true)] {
                let mut dead = 0_u32;
                let mut actual = 0_u32;
                let mut text = [0_u16; 4];
                let status = unsafe {
                    UCKeyTranslate(
                        layout.cast(),
                        code,
                        0,
                        modifier_state,
                        keyboard_type,
                        1,
                        &mut dead,
                        text.len() as u32,
                        &mut actual,
                        text.as_mut_ptr(),
                    )
                };
                if status == 0
                    && actual == 1
                    && char::from_u32(u32::from(text[0]))
                        .is_some_and(|value| value.eq_ignore_ascii_case(&character))
                {
                    best = Some((code, shift));
                    break;
                }
            }
            if best.is_some() {
                break;
            }
        }
        best.ok_or_else(|| format!("Key {character} is unavailable on the current layout"))
    })();
    unsafe { CFRelease(source) };
    result
}

fn post(code: u16, down: bool, flags: u64) -> Result<(), String> {
    let event = unsafe { CGEventCreateKeyboardEvent(std::ptr::null(), code, down) };
    if event.is_null() {
        return Err("Could not create a keyboard event".into());
    }
    unsafe {
        CGEventSetFlags(event, flags);
        CGEventPost(SESSION_EVENT_TAP, event);
        CFRelease(event);
    }
    Ok(())
}

fn send_sync(character: char, modifiers: Vec<&'static str>) -> Result<(), String> {
    if !unsafe { AXIsProcessTrusted() } {
        return Err("Allow 3Decks in macOS Accessibility settings to send shortcuts".into());
    }
    let (key, implicit_shift) = key_code(character)?;
    let mut chord = Vec::new();
    for modifier in modifiers {
        let item = match modifier {
            "command down" => (55, COMMAND),
            "shift down" => (56, SHIFT),
            "control down" => (59, CONTROL),
            "option down" => (58, OPTION),
            _ => return Err("Unsupported shortcut modifier".into()),
        };
        if !chord.contains(&item) {
            chord.push(item);
        }
    }
    if implicit_shift && !chord.iter().any(|(_, flag)| *flag == SHIFT) {
        chord.push((56, SHIFT));
    }
    let mut flags = 0_u64;
    let mut pressed = Vec::new();
    let result = (|| {
        for &(code, flag) in &chord {
            flags |= flag;
            post(code, true, flags)?;
            pressed.push((code, flag));
        }
        post(key, true, flags)?;
        post(key, false, flags)
    })();
    for (code, flag) in pressed.into_iter().rev() {
        flags &= !flag;
        let _ = post(code, false, flags);
    }
    result
}

pub async fn send(character: char, modifiers: Vec<&'static str>) -> Result<(), String> {
    tokio::task::spawn_blocking(move || send_sync(character, modifiers))
        .await
        .map_err(|error| error.to_string())?
}

#[cfg(test)]
mod tests {
    #[test]
    #[ignore = "requires an active macOS keyboard layout"]
    fn resolves_shortcuts_on_current_layout() {
        assert!(super::key_code('a').is_ok());
        assert!(super::key_code('1').is_ok());
    }
}

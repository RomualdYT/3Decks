//! Layout-aware Quartz shortcuts. Only the validated key and modifiers cross
//! this boundary; no AppleScript or command string is constructed.
use std::ffi::c_void;

const SHIFT: u64 = 1 << 17;
const CONTROL: u64 = 1 << 18;
const OPTION: u64 = 1 << 19;
const COMMAND: u64 = 1 << 20;
const SESSION_EVENT_TAP: u32 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Key {
    Character(char),
    Virtual(u16),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Modifier {
    Command,
    Control,
    Option,
    Shift,
}

impl Modifier {
    fn event(self) -> (u16, u64) {
        match self {
            Self::Command => (55, COMMAND),
            Self::Control => (59, CONTROL),
            Self::Option => (58, OPTION),
            Self::Shift => (56, SHIFT),
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
struct Shortcut {
    key: Key,
    modifiers: Vec<Modifier>,
}

fn named_key(name: &str) -> Option<u16> {
    Some(match name {
        "escape" | "esc" | "echap" | "echappement" => 53,
        "return" | "enter" | "entree" | "retour" => 36,
        "tab" | "tabulation" => 48,
        "space" | "espace" => 49,
        "backspace" | "delete" => 51,
        "forward_delete" | "suppr" | "supprimer" => 117,
        "left" | "gauche" => 123,
        "right" | "droite" => 124,
        "up" | "haut" => 126,
        "down" | "bas" => 125,
        "home" | "debut" => 115,
        "end" | "fin" => 119,
        "pageup" => 116,
        "pagedown" => 121,
        // A Windows Print Screen key is normally presented as F13 on macOS.
        "printscreen" => 105,
        "f1" => 122,
        "f2" => 120,
        "f3" => 99,
        "f4" => 118,
        "f5" => 96,
        "f6" => 97,
        "f7" => 98,
        "f8" => 100,
        "f9" => 101,
        "f10" => 109,
        "f11" => 103,
        "f12" => 111,
        _ => return None,
    })
}

fn parse_shortcut(text: &str) -> Result<Shortcut, String> {
    let mut modifiers = Vec::new();
    let mut target = None;
    for part in text
        .split('+')
        .map(str::trim)
        .filter(|part| !part.is_empty())
    {
        let name = part.to_ascii_lowercase();
        let modifier = match name.as_str() {
            "cmd" | "command" | "win" | "super" | "meta" => Some(Modifier::Command),
            "ctrl" | "control" => Some(Modifier::Control),
            "alt" | "opt" | "option" => Some(Modifier::Option),
            "shift" => Some(Modifier::Shift),
            _ => None,
        };
        if let Some(modifier) = modifier {
            if !modifiers.contains(&modifier) {
                modifiers.push(modifier);
            }
            continue;
        }
        if target.is_some() {
            return Err("A shortcut must contain exactly one key".into());
        }
        let key = if let Some(code) = named_key(&name) {
            Key::Virtual(code)
        } else if name.len() == 1 && name.as_bytes()[0].is_ascii_alphanumeric() {
            Key::Character(name.chars().next().unwrap())
        } else {
            return Err(format!("Unknown shortcut key: {part}"));
        };
        target = Some(key);
    }
    let key = target.ok_or("Shortcut key missing")?;
    Ok(Shortcut { key, modifiers })
}

pub(crate) fn validate(keys: &str) -> Result<(), String> {
    parse_shortcut(keys).map(|_| ())
}

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

fn send_sync(text: &str) -> Result<(), String> {
    let shortcut = parse_shortcut(text)?;
    if !unsafe { AXIsProcessTrusted() } {
        return Err("Allow 3Decks in macOS Accessibility settings to send shortcuts".into());
    }
    let (key, implicit_shift) = match shortcut.key {
        Key::Character(character) => key_code(character)?,
        Key::Virtual(code) => (code, false),
    };
    let mut chord = Vec::new();
    for modifier in shortcut.modifiers {
        let item = modifier.event();
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

pub async fn send(keys: &str) -> Result<(), String> {
    let keys = keys.to_owned();
    tokio::task::spawn_blocking(move || send_sync(&keys))
        .await
        .map_err(|error| error.to_string())?
}

#[cfg(test)]
mod tests {
    use super::{parse_shortcut, Key, Modifier};

    #[test]
    fn parses_every_named_key_from_the_python_catalog() {
        for (name, code) in [
            ("escape", 53),
            ("return", 36),
            ("tab", 48),
            ("space", 49),
            ("backspace", 51),
            ("forward_delete", 117),
            ("left", 123),
            ("right", 124),
            ("up", 126),
            ("down", 125),
            ("home", 115),
            ("end", 119),
            ("pageup", 116),
            ("pagedown", 121),
            ("printscreen", 105),
            ("f1", 122),
            ("f2", 120),
            ("f3", 99),
            ("f4", 118),
            ("f5", 96),
            ("f6", 97),
            ("f7", 98),
            ("f8", 100),
            ("f9", 101),
            ("f10", 109),
            ("f11", 103),
            ("f12", 111),
        ] {
            assert_eq!(
                parse_shortcut(name).unwrap().key,
                Key::Virtual(code),
                "{name}"
            );
        }
    }

    #[test]
    fn accepts_legacy_aliases_and_rejects_extra_keys() {
        let shortcut = parse_shortcut("shift+cmd+shift+EcHaP").unwrap();
        assert_eq!(shortcut.key, Key::Virtual(53));
        assert_eq!(shortcut.modifiers, [Modifier::Shift, Modifier::Command]);
        assert_eq!(parse_shortcut("cmd+f12").unwrap().key, Key::Virtual(111));
        assert!(parse_shortcut("cmd+left+right").is_err());
        assert!(parse_shortcut("cmd+x\"; display dialog \"bad").is_err());
        assert!(parse_shortcut("cmd+unknown").is_err());
    }

    #[test]
    #[ignore = "requires an active macOS keyboard layout"]
    fn resolves_shortcuts_on_current_layout() {
        assert!(super::key_code('a').is_ok());
        assert!(super::key_code('1').is_ok());
    }
}

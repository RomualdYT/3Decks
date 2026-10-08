//! Layout-aware synthetic keyboard input for Windows.
//!
//! The input grammar matches the macOS adapter and the Python action catalog:
//! modifier names joined with `+`, followed by one alphanumeric or named key.
//! All Win32 calls stay on a blocking worker and no native handles escape.

use windows::Win32::UI::Input::KeyboardAndMouse::{
    GetKeyboardLayout, MapVirtualKeyExW, SendInput, VkKeyScanExW, HKL, INPUT, INPUT_0,
    INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, MAPVK_VK_TO_VSC_EX,
    VIRTUAL_KEY, VK_BACK, VK_CONTROL, VK_DELETE, VK_DOWN, VK_END, VK_ESCAPE, VK_F1, VK_F10, VK_F11,
    VK_F12, VK_HOME, VK_LEFT, VK_LWIN, VK_MENU, VK_NEXT, VK_PRIOR, VK_RETURN, VK_RIGHT, VK_SHIFT,
    VK_SNAPSHOT, VK_SPACE, VK_TAB, VK_UP,
};
use windows::Win32::UI::WindowsAndMessaging::{GetForegroundWindow, GetWindowThreadProcessId};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Key {
    virtual_key: VIRTUAL_KEY,
    extended: bool,
    implicit_shift: bool,
    implicit_control: bool,
    implicit_alt: bool,
}

fn named_key(name: &str) -> Option<Key> {
    let (virtual_key, extended) = match name {
        "escape" | "esc" | "echap" | "échappement" | "echappement" => (VK_ESCAPE, false),
        "return" | "enter" | "entree" | "entrée" | "retour" => (VK_RETURN, false),
        "tab" | "tabulation" => (VK_TAB, false),
        "space" | "espace" => (VK_SPACE, false),
        "backspace" | "delete" | "retour_arriere" | "retour arrière" => (VK_BACK, false),
        "forward_delete" | "suppr" | "supprimer" => (VK_DELETE, true),
        "left" | "gauche" | "flèche gauche" => (VK_LEFT, true),
        "right" | "droite" | "flèche droite" => (VK_RIGHT, true),
        "up" | "haut" | "flèche haut" => (VK_UP, true),
        "down" | "bas" | "flèche bas" => (VK_DOWN, true),
        "home" | "debut" | "début" => (VK_HOME, true),
        "end" | "fin" => (VK_END, true),
        "pageup" | "page_up" | "page up" => (VK_PRIOR, true),
        "pagedown" | "page_down" | "page down" => (VK_NEXT, true),
        "printscreen" | "print_screen" | "print screen" | "impr. écran" => (VK_SNAPSHOT, true),
        "f1" => (VK_F1, false),
        "f2" => (VIRTUAL_KEY(VK_F1.0 + 1), false),
        "f3" => (VIRTUAL_KEY(VK_F1.0 + 2), false),
        "f4" => (VIRTUAL_KEY(VK_F1.0 + 3), false),
        "f5" => (VIRTUAL_KEY(VK_F1.0 + 4), false),
        "f6" => (VIRTUAL_KEY(VK_F1.0 + 5), false),
        "f7" => (VIRTUAL_KEY(VK_F1.0 + 6), false),
        "f8" => (VIRTUAL_KEY(VK_F1.0 + 7), false),
        "f9" => (VIRTUAL_KEY(VK_F1.0 + 8), false),
        "f10" => (VK_F10, false),
        "f11" => (VK_F11, false),
        "f12" => (VK_F12, false),
        _ => return None,
    };
    Some(Key {
        virtual_key,
        extended,
        implicit_shift: false,
        implicit_control: false,
        implicit_alt: false,
    })
}

fn current_layout() -> HKL {
    let foreground = unsafe { GetForegroundWindow() };
    if !foreground.0.is_null() {
        let thread = unsafe { GetWindowThreadProcessId(foreground, None) };
        if thread != 0 {
            let layout = unsafe { GetKeyboardLayout(thread) };
            if !layout.0.is_null() {
                return layout;
            }
        }
    }
    unsafe { GetKeyboardLayout(0) }
}

fn character_key(character: char, layout: HKL) -> Result<Key, String> {
    let mapped = unsafe { VkKeyScanExW(character as u16, layout) };
    if mapped == -1 {
        return Err(format!(
            "Key {character} is unavailable on the active keyboard layout"
        ));
    }
    let bits = mapped as u16;
    let modifiers = (bits >> 8) as u8;
    Ok(Key {
        virtual_key: VIRTUAL_KEY(bits & 0xff),
        extended: false,
        implicit_shift: modifiers & 1 != 0,
        implicit_control: modifiers & 2 != 0,
        implicit_alt: modifiers & 4 != 0,
    })
}

fn modifier(name: &str) -> Option<VIRTUAL_KEY> {
    Some(match name {
        "cmd" | "command" | "win" | "super" | "meta" => VK_LWIN,
        "ctrl" | "control" => VK_CONTROL,
        "alt" | "opt" | "option" => VK_MENU,
        "shift" => VK_SHIFT,
        _ => return None,
    })
}

fn parse_shortcut(text: &str, layout: HKL) -> Result<(Vec<VIRTUAL_KEY>, Key), String> {
    let parts: Vec<_> = text
        .split('+')
        .map(str::trim)
        .filter(|part| !part.is_empty())
        .collect();
    let (key_name, modifier_names) = parts.split_last().ok_or("Shortcut key missing")?;
    let mut modifiers = Vec::new();
    for part in modifier_names {
        let key = modifier(&part.to_lowercase())
            .ok_or_else(|| format!("Unknown shortcut modifier: {part}"))?;
        if modifiers.contains(&key) {
            return Err("Duplicate shortcut modifier".into());
        }
        modifiers.push(key);
    }
    let normalized = key_name.to_lowercase();
    let key = if let Some(key) = named_key(&normalized) {
        key
    } else {
        let mut characters = normalized.chars();
        let character = characters.next().ok_or("Shortcut key missing")?;
        if characters.next().is_some() || !character.is_ascii_alphanumeric() {
            return Err(format!("Unknown shortcut key: {key_name}"));
        }
        character_key(character, layout)?
    };
    for (required, virtual_key) in [
        (key.implicit_control, VK_CONTROL),
        (key.implicit_alt, VK_MENU),
        (key.implicit_shift, VK_SHIFT),
    ] {
        if required && !modifiers.contains(&virtual_key) {
            modifiers.push(virtual_key);
        }
    }
    Ok((modifiers, key))
}

fn keyboard_event(key: VIRTUAL_KEY, extended: bool, release: bool) -> INPUT {
    let scan_code =
        unsafe { MapVirtualKeyExW(key.0.into(), MAPVK_VK_TO_VSC_EX, Some(current_layout())) };
    let mut flags = Default::default();
    if extended || scan_code > 0xff {
        flags |= KEYEVENTF_EXTENDEDKEY;
    }
    if release {
        flags |= KEYEVENTF_KEYUP;
    }
    INPUT {
        r#type: INPUT_KEYBOARD,
        Anonymous: INPUT_0 {
            ki: KEYBDINPUT {
                wVk: key,
                dwFlags: flags,
                ..Default::default()
            },
        },
    }
}

fn send_sync(text: &str) -> Result<(), String> {
    let layout = current_layout();
    let (modifiers, key) = parse_shortcut(text, layout)?;
    let mut pressed = modifiers.clone();
    pressed.push(key.virtual_key);
    let mut events = Vec::with_capacity(pressed.len() * 2);
    for modifier in &modifiers {
        events.push(keyboard_event(*modifier, false, false));
    }
    events.push(keyboard_event(key.virtual_key, key.extended, false));
    events.push(keyboard_event(key.virtual_key, key.extended, true));
    for modifier in modifiers.iter().rev() {
        events.push(keyboard_event(*modifier, false, true));
    }
    let sent = unsafe { SendInput(&events, std::mem::size_of::<INPUT>() as i32) };
    if sent as usize == events.len() {
        return Ok(());
    }

    // A partial SendInput can leave a key logically pressed. Release the whole chord.
    let releases: Vec<_> = pressed
        .iter()
        .rev()
        .map(|key| keyboard_event(*key, false, true))
        .collect();
    unsafe { SendInput(&releases, std::mem::size_of::<INPUT>() as i32) };
    Err("Windows rejected synthetic input; check the foreground app's integrity level".into())
}

pub async fn hotkey(keys: &str) -> Result<(), String> {
    let keys = keys.to_owned();
    tokio::task::spawn_blocking(move || send_sync(&keys))
        .await
        .map_err(|error| error.to_string())?
}

#[cfg(test)]
mod tests {
    use super::{modifier, named_key};
    use windows::Win32::UI::Input::KeyboardAndMouse::{VK_ESCAPE, VK_F1, VK_LEFT, VK_RETURN};

    #[test]
    fn maps_python_catalog_named_keys_to_windows_virtual_keys() {
        for (name, key) in [
            ("escape", VK_ESCAPE),
            ("return", VK_RETURN),
            ("left", VK_LEFT),
            ("f1", VK_F1),
            ("echap", VK_ESCAPE),
            ("entrée", VK_RETURN),
        ] {
            assert_eq!(named_key(name).unwrap().virtual_key, key, "{name}");
        }
        for number in 1..=12 {
            assert!(named_key(&format!("f{number}")).is_some());
        }
        for name in [
            "right",
            "up",
            "down",
            "home",
            "end",
            "pageup",
            "pagedown",
            "forward_delete",
            "printscreen",
        ] {
            assert!(named_key(name).unwrap().extended, "{name}");
        }
    }

    #[test]
    fn accepts_common_modifier_aliases_and_rejects_unknown_names() {
        for name in [
            "cmd", "command", "win", "super", "meta", "ctrl", "control", "alt", "option", "shift",
        ] {
            assert!(modifier(name).is_some());
        }
        assert!(named_key("f13").is_none());
        assert!(modifier("fn").is_none());
    }
}

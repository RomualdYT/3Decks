//! Synthetic key events. Input is restricted to one letter/digit and known modifiers.
use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP, VIRTUAL_KEY,
    VK_CONTROL, VK_LWIN, VK_MEDIA_NEXT_TRACK, VK_MEDIA_PLAY_PAUSE, VK_MEDIA_PREV_TRACK, VK_MENU,
    VK_SHIFT,
};

fn event(key: VIRTUAL_KEY, release: bool) -> INPUT {
    INPUT {
        r#type: INPUT_KEYBOARD,
        Anonymous: INPUT_0 {
            ki: KEYBDINPUT {
                wVk: key,
                dwFlags: if release {
                    KEYEVENTF_KEYUP
                } else {
                    Default::default()
                },
                ..Default::default()
            },
        },
    }
}

fn send(keys: &[VIRTUAL_KEY]) -> Result<(), String> {
    let events: Vec<INPUT> = keys
        .iter()
        .copied()
        .map(|key| event(key, false))
        .chain(keys.iter().rev().copied().map(|key| event(key, true)))
        .collect();
    let sent = unsafe { SendInput(&events, std::mem::size_of::<INPUT>() as i32) };
    if sent as usize == events.len() {
        Ok(())
    } else {
        // A partial insertion could leave a modifier pressed. Release every key.
        let releases: Vec<INPUT> = keys
            .iter()
            .rev()
            .copied()
            .map(|key| event(key, true))
            .collect();
        unsafe { SendInput(&releases, std::mem::size_of::<INPUT>() as i32) };
        Err("Windows rejected synthetic input; check the foreground app's integrity level".into())
    }
}

pub fn media(command: &str) -> Result<(), String> {
    let key = match command {
        "playpause" => VK_MEDIA_PLAY_PAUSE,
        "next track" => VK_MEDIA_NEXT_TRACK,
        "previous track" => VK_MEDIA_PREV_TRACK,
        _ => return Err("Unsupported media command".into()),
    };
    send(&[key])
}

pub fn hotkey(keys: &str) -> Result<(), String> {
    let parts: Vec<_> = keys.split('+').map(str::trim).collect();
    let key = parts.last().ok_or("Empty shortcut")?;
    let mut chars = key.chars();
    let character = chars.next().ok_or("Empty shortcut")?;
    if chars.next().is_some() || !character.is_ascii_alphanumeric() {
        return Err("Only a single letter or digit is supported as shortcut key".into());
    }
    let mut chord = Vec::new();
    for part in &parts[..parts.len() - 1] {
        let modifier = match part.to_ascii_lowercase().as_str() {
            "cmd" | "command" | "meta" | "win" => VK_LWIN,
            "shift" => VK_SHIFT,
            "ctrl" | "control" => VK_CONTROL,
            "alt" | "option" => VK_MENU,
            _ => return Err(format!("Unknown shortcut modifier: {part}")),
        };
        if chord.contains(&modifier) {
            return Err("Duplicate shortcut modifier".into());
        }
        chord.push(modifier);
    }
    chord.push(VIRTUAL_KEY(character.to_ascii_uppercase() as u16));
    send(&chord)
}

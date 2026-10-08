//! User initiated volume control for the active media app's WASAPI sessions.
//!
//! The process is resolved from GSMTC's active source id. Windows may expose
//! several audio sessions for one process, so volume changes are applied to
//! every matching active session on the default multimedia output.

use super::audio::ComApartment;
use windows::core::Interface;
use windows::Win32::Foundation::CloseHandle;
use windows::Win32::Media::Audio::{
    eMultimedia, eRender, AudioSessionStateActive, IAudioSessionControl2, IAudioSessionManager2,
    IMMDeviceEnumerator, ISimpleAudioVolume, MMDeviceEnumerator,
};
use windows::Win32::System::Com::{CoCreateInstance, CLSCTX_ALL};
use windows::Win32::System::Threading::{
    OpenProcess, QueryFullProcessImageNameW, PROCESS_NAME_FORMAT, PROCESS_QUERY_LIMITED_INFORMATION,
};

fn source_executable(source_id: &str) -> Option<String> {
    let id = source_id.to_ascii_lowercase();
    let known = if id.contains("spotify") {
        "spotify.exe"
    } else if id.contains("msedge") || id.contains("microsoftedge") {
        "msedge.exe"
    } else if id.contains("chrome") {
        "chrome.exe"
    } else if id.contains("firefox") {
        "firefox.exe"
    } else if id.contains("applemusic") || id.contains("apple.music") {
        "applemusic.exe"
    } else if id.contains("vlc") {
        "vlc.exe"
    } else if id.ends_with(".exe") {
        return id.rsplit(['\\', '/']).next().map(str::to_owned);
    } else {
        let tail = id.rsplit('!').next().unwrap_or(&id);
        let name = tail.rsplit('.').next().unwrap_or(tail);
        if name.is_empty()
            || !name
                .chars()
                .all(|character| character.is_ascii_alphanumeric())
        {
            return None;
        }
        return Some(format!("{name}.exe"));
    };
    Some(known.to_owned())
}

fn process_executable(pid: u32) -> Option<String> {
    let process = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) }.ok()?;
    let mut path = vec![0_u16; 32768];
    let mut length = path.len() as u32;
    let result = unsafe {
        QueryFullProcessImageNameW(
            process,
            PROCESS_NAME_FORMAT(0),
            windows::core::PWSTR(path.as_mut_ptr()),
            &mut length,
        )
    };
    let _ = unsafe { CloseHandle(process) };
    result.ok()?;
    Some(
        String::from_utf16_lossy(&path[..length as usize])
            .rsplit(['\\', '/'])
            .next()?
            .to_ascii_lowercase(),
    )
}

fn matching_sessions(source_id: &str) -> Result<Vec<ISimpleAudioVolume>, String> {
    let expected = source_executable(source_id)
        .ok_or_else(|| "The active media app cannot be matched to an audio session".to_owned())?;
    let enumerator: IMMDeviceEnumerator =
        unsafe { CoCreateInstance(&MMDeviceEnumerator, None, CLSCTX_ALL) }
            .map_err(|error| error.to_string())?;
    let device = unsafe { enumerator.GetDefaultAudioEndpoint(eRender, eMultimedia) }
        .map_err(|error| error.to_string())?;
    let manager: IAudioSessionManager2 =
        unsafe { device.Activate(CLSCTX_ALL, None) }.map_err(|error| error.to_string())?;
    let sessions = unsafe { manager.GetSessionEnumerator() }.map_err(|error| error.to_string())?;
    let count = unsafe { sessions.GetCount() }.map_err(|error| error.to_string())?;
    let mut matching = Vec::new();
    for index in 0..count {
        let Ok(session) = (unsafe { sessions.GetSession(index) }) else {
            continue;
        };
        let Ok(control) = session.cast::<IAudioSessionControl2>() else {
            continue;
        };
        if unsafe { control.IsSystemSoundsSession() } == windows::core::HRESULT(0) {
            continue;
        }
        if unsafe { control.GetState() }.ok() != Some(AudioSessionStateActive) {
            continue;
        }
        let Ok(pid) = (unsafe { control.GetProcessId() }) else {
            continue;
        };
        if process_executable(pid).as_deref() != Some(expected.as_str()) {
            continue;
        }
        if let Ok(volume) = session.cast::<ISimpleAudioVolume>() {
            matching.push(volume);
        }
    }
    Ok(matching)
}

pub(crate) fn volume_for_source(source_id: &str) -> Result<Option<u8>, String> {
    let _apartment = ComApartment::enter()?;
    let sessions = matching_sessions(source_id)?;
    Ok(average_volume(&sessions))
}

fn average_volume(sessions: &[ISimpleAudioVolume]) -> Option<u8> {
    let (total, count) = sessions
        .iter()
        .filter_map(|session| unsafe { session.GetMasterVolume().ok() })
        .filter(|volume| volume.is_finite())
        .fold((0.0_f32, 0_u32), |(total, count), volume| {
            (total + volume, count + 1)
        });
    (count > 0).then(|| ((total / count as f32).clamp(0.0, 1.0) * 100.0).round() as u8)
}

pub async fn set_active_media_volume(value: u8) -> Result<(), String> {
    let source_id = super::media::active_source_app_id()
        .await?
        .ok_or("No active media session")?;
    tokio::task::spawn_blocking(move || {
        let _apartment = ComApartment::enter()?;
        let sessions = matching_sessions(&source_id)?;
        if sessions.is_empty() {
            return Err("No active audio session matched the current media app".into());
        }
        for session in sessions {
            unsafe { session.SetMasterVolume(f32::from(value) / 100.0, std::ptr::null()) }
                .map_err(|error| error.to_string())?;
        }
        Ok(())
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn change_active_media_volume(direction: i8, step: u8) -> Result<(), String> {
    let source_id = super::media::active_source_app_id()
        .await?
        .ok_or("No active media session")?;
    tokio::task::spawn_blocking(move || {
        let _apartment = ComApartment::enter()?;
        let sessions = matching_sessions(&source_id)?;
        let current = average_volume(&sessions)
            .ok_or("No active audio session matched the current media app")?;
        let next = (i16::from(current) + i16::from(direction) * i16::from(step)).clamp(0, 100);
        for session in sessions {
            unsafe { session.SetMasterVolume(next as f32 / 100.0, std::ptr::null()) }
                .map_err(|error| error.to_string())?;
        }
        Ok(())
    })
    .await
    .map_err(|error| error.to_string())?
}

#[cfg(test)]
mod tests {
    use super::source_executable;

    #[test]
    fn maps_common_gsmtc_source_ids_to_process_names() {
        for (source, expected) in [
            ("Spotify.exe", "spotify.exe"),
            ("Microsoft.MicrosoftEdge_123!MSEdge", "msedge.exe"),
            ("Google.Chrome_123!Chrome", "chrome.exe"),
            ("AppleInc.AppleMusicWin_123!AppleMusic", "applemusic.exe"),
        ] {
            assert_eq!(source_executable(source).as_deref(), Some(expected));
        }
        assert_eq!(
            source_executable("Unknown!Player"),
            Some("player.exe".into())
        );
        assert_eq!(source_executable("!!!"), None);
    }
}

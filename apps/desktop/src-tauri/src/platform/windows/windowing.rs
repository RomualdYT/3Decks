//! Top-level desktop windows. Handles are revalidated before activation.
use crate::platform::windowing::Window;
use windows::core::{BOOL, PWSTR};
use windows::Win32::Foundation::{CloseHandle, HWND, LPARAM};
use windows::Win32::System::Threading::{
    OpenProcess, QueryFullProcessImageNameW, PROCESS_NAME_WIN32, PROCESS_QUERY_LIMITED_INFORMATION,
};
use windows::Win32::UI::WindowsAndMessaging::{
    EnumWindows, GetWindow, GetWindowTextLengthW, GetWindowTextW, GetWindowThreadProcessId,
    IsIconic, IsWindowVisible, SetForegroundWindow, ShowWindow, GW_OWNER, SW_RESTORE,
};

pub(crate) fn process_name(pid: u32) -> Option<String> {
    let handle = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) }.ok()?;
    let mut path = [0_u16; 1024];
    let mut length = path.len() as u32;
    let result = unsafe {
        QueryFullProcessImageNameW(
            handle,
            PROCESS_NAME_WIN32,
            PWSTR(path.as_mut_ptr()),
            &mut length,
        )
    };
    let _ = unsafe { CloseHandle(handle) };
    result.ok()?;
    let path = String::from_utf16_lossy(&path[..length as usize]);
    std::path::Path::new(&path)
        .file_stem()
        .map(|name| name.to_string_lossy().into_owned())
}

unsafe extern "system" fn collect(hwnd: HWND, context: LPARAM) -> BOOL {
    let windows = unsafe { &mut *(context.0 as *mut Vec<Window>) };
    if windows.len() >= 32 {
        return false.into();
    }
    if !unsafe { IsWindowVisible(hwnd) }.as_bool() || unsafe { GetWindow(hwnd, GW_OWNER) }.is_ok() {
        return true.into();
    }
    let length = unsafe { GetWindowTextLengthW(hwnd) };
    if !(1..=2048).contains(&length) {
        return true.into();
    }
    let mut text = vec![0_u16; length as usize + 1];
    let count = unsafe { GetWindowTextW(hwnd, &mut text) };
    if count <= 0 {
        return true.into();
    }
    let mut pid = 0;
    unsafe { GetWindowThreadProcessId(hwnd, Some(&mut pid)) };
    if pid == 0 {
        return true.into();
    }
    windows.push(Window {
        app: process_name(pid).unwrap_or_else(|| format!("PID {pid}")),
        title: String::from_utf16_lossy(&text[..count as usize]),
        pid: i64::from(pid),
        number: hwnd.0 as isize as i64,
    });
    true.into()
}

fn list_sync() -> Vec<Window> {
    let mut windows = Vec::new();
    let context = LPARAM((&mut windows as *mut Vec<Window>) as isize);
    // Returning false at the 32-window cap is intentional; the collected list is valid.
    let _ = unsafe { EnumWindows(Some(collect), context) };
    windows
}

pub async fn list() -> Vec<Window> {
    tokio::task::spawn_blocking(list_sync)
        .await
        .unwrap_or_default()
}

pub async fn focus(window: &Window) -> Result<&'static str, String> {
    let window = window.clone();
    tokio::task::spawn_blocking(move || {
        let hwnd = HWND(window.number as isize as *mut std::ffi::c_void);
        let mut pid = 0;
        unsafe { GetWindowThreadProcessId(hwnd, Some(&mut pid)) };
        if pid == 0 || i64::from(pid) != window.pid {
            return Err("Window is no longer available".into());
        }
        if unsafe { IsIconic(hwnd) }.as_bool() {
            let _ = unsafe { ShowWindow(hwnd, SW_RESTORE) };
        }
        if unsafe { SetForegroundWindow(hwnd) }.as_bool() {
            Ok("Window focused")
        } else {
            Err("Windows denied foreground activation for this window".into())
        }
    })
    .await
    .map_err(|error| error.to_string())?
}

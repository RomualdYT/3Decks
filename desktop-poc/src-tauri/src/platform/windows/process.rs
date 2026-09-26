//! Requests a graceful close of all top-level windows belonging to a named app.
//! Windows applications may show a save dialog or ignore WM_CLOSE.
use windows::core::BOOL;
use windows::Win32::Foundation::{HWND, LPARAM, WPARAM};
use windows::Win32::UI::WindowsAndMessaging::{
    EnumWindows, GetWindow, GetWindowThreadProcessId, IsWindowVisible, PostMessageW, GW_OWNER,
    WM_CLOSE,
};

struct CloseRequest {
    name: String,
    posted: usize,
}

unsafe extern "system" fn request_close(hwnd: HWND, context: LPARAM) -> BOOL {
    let request = unsafe { &mut *(context.0 as *mut CloseRequest) };
    if !unsafe { IsWindowVisible(hwnd) }.as_bool() || unsafe { GetWindow(hwnd, GW_OWNER) }.is_ok() {
        return true.into();
    }
    let mut pid = 0;
    unsafe { GetWindowThreadProcessId(hwnd, Some(&mut pid)) };
    if pid == 0 {
        return true.into();
    }
    let matches = super::windowing::process_name(pid)
        .is_some_and(|name| name.eq_ignore_ascii_case(&request.name));
    if matches && unsafe { PostMessageW(Some(hwnd), WM_CLOSE, WPARAM(0), LPARAM(0)) }.is_ok() {
        request.posted += 1;
    }
    true.into()
}

pub async fn quit_app(target: &str) -> Result<(), String> {
    let name = std::path::Path::new(target)
        .file_stem()
        .and_then(|name| name.to_str())
        .filter(|name| !name.is_empty())
        .ok_or("Invalid application target")?
        .to_owned();
    tokio::task::spawn_blocking(move || {
        let mut request = CloseRequest { name, posted: 0 };
        let context = LPARAM((&mut request as *mut CloseRequest) as isize);
        unsafe { EnumWindows(Some(request_close), context) }.map_err(|error| error.to_string())?;
        if request.posted > 0 {
            Ok(())
        } else {
            Err(format!("No closable window found for {}", request.name))
        }
    })
    .await
    .map_err(|error| error.to_string())?
}

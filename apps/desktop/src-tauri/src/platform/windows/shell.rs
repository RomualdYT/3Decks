//! Shell integration through ShellExecuteW and the session API.
use windows::core::{w, PCWSTR};
use windows::Win32::System::Shutdown::LockWorkStation;
use windows::Win32::UI::Shell::ShellExecuteW;
use windows::Win32::UI::WindowsAndMessaging::SW_SHOWNORMAL;

pub async fn open(target: &str) -> Result<(), String> {
    let target = target.to_owned();
    tokio::task::spawn_blocking(move || {
        if target.contains('\0') {
            return Err("Invalid shell target".into());
        }
        let wide: Vec<u16> = target.encode_utf16().chain(std::iter::once(0)).collect();
        let result = unsafe {
            ShellExecuteW(
                None,
                w!("open"),
                PCWSTR(wide.as_ptr()),
                PCWSTR::null(),
                PCWSTR::null(),
                SW_SHOWNORMAL,
            )
        };
        if result.0 as isize > 32 {
            Ok(())
        } else {
            Err(format!(
                "Windows could not open {target} (ShellExecute code {})",
                result.0 as isize
            ))
        }
    })
    .await
    .map_err(|error| error.to_string())?
}

pub async fn lock_session() -> Result<(), String> {
    tokio::task::spawn_blocking(|| unsafe { LockWorkStation().map_err(|error| error.to_string()) })
        .await
        .map_err(|error| error.to_string())?
}

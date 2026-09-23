//! WASAPI endpoint controls, isolated on blocking worker threads.
use windows::Win32::Media::Audio::Endpoints::IAudioEndpointVolume;
use windows::Win32::Media::Audio::{
    eCapture, eMultimedia, eRender, EDataFlow, IMMDeviceEnumerator, MMDeviceEnumerator,
};
use windows::Win32::System::Com::{
    CoCreateInstance, CoInitializeEx, CoUninitialize, CLSCTX_ALL, COINIT_MULTITHREADED,
};

struct ComApartment;

impl ComApartment {
    fn enter() -> Result<Self, String> {
        // Each Tokio blocking worker owns its COM apartment for the duration of the call.
        unsafe { CoInitializeEx(None, COINIT_MULTITHREADED) }
            .ok()
            .map_err(|error| error.to_string())?;
        Ok(Self)
    }
}

impl Drop for ComApartment {
    fn drop(&mut self) {
        unsafe { CoUninitialize() };
    }
}

fn with_endpoint<T>(
    flow: EDataFlow,
    operation: impl FnOnce(&IAudioEndpointVolume) -> Result<T, String>,
) -> Result<T, String> {
    let _apartment = ComApartment::enter()?;
    let enumerator: IMMDeviceEnumerator =
        unsafe { CoCreateInstance(&MMDeviceEnumerator, None, CLSCTX_ALL) }
            .map_err(|error| error.to_string())?;
    let device = unsafe { enumerator.GetDefaultAudioEndpoint(flow, eMultimedia) }
        .map_err(|error| error.to_string())?;
    let endpoint: IAudioEndpointVolume =
        unsafe { device.Activate(CLSCTX_ALL, None) }.map_err(|error| error.to_string())?;
    operation(&endpoint)
}

pub fn output_state() -> Result<(u8, bool), String> {
    with_endpoint(eRender, |endpoint| {
        let volume =
            unsafe { endpoint.GetMasterVolumeLevelScalar() }.map_err(|error| error.to_string())?;
        let muted = unsafe { endpoint.GetMute() }.map_err(|error| error.to_string())?;
        Ok((
            (volume.clamp(0.0, 1.0) * 100.0).round() as u8,
            muted.as_bool(),
        ))
    })
}

pub fn input_volume() -> Result<u8, String> {
    with_endpoint(eCapture, |endpoint| {
        let volume =
            unsafe { endpoint.GetMasterVolumeLevelScalar() }.map_err(|error| error.to_string())?;
        let muted = unsafe { endpoint.GetMute() }.map_err(|error| error.to_string())?;
        Ok(if muted.as_bool() {
            0
        } else {
            (volume.clamp(0.0, 1.0) * 100.0).round() as u8
        })
    })
}

pub fn set_output_volume(value: u8) -> Result<(), String> {
    with_endpoint(eRender, |endpoint| {
        unsafe { endpoint.SetMasterVolumeLevelScalar(f32::from(value) / 100.0, std::ptr::null()) }
            .map_err(|error| error.to_string())
    })
}

pub fn set_output_muted(value: bool) -> Result<(), String> {
    with_endpoint(eRender, |endpoint| {
        unsafe { endpoint.SetMute(value, std::ptr::null()) }.map_err(|error| error.to_string())
    })
}

pub fn set_input_volume(value: u8) -> Result<(), String> {
    with_endpoint(eCapture, |endpoint| {
        if value > 0 {
            unsafe {
                endpoint.SetMasterVolumeLevelScalar(f32::from(value) / 100.0, std::ptr::null())
            }
            .map_err(|error| error.to_string())?;
        }
        unsafe { endpoint.SetMute(value == 0, std::ptr::null()) }.map_err(|error| error.to_string())
    })
}

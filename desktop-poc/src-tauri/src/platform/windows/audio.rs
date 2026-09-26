//! WASAPI endpoint controls, isolated on blocking worker threads.
use crate::platform::audio::Output;
use windows::Win32::Devices::FunctionDiscovery::PKEY_Device_FriendlyName;
use windows::Win32::Media::Audio::Endpoints::IAudioEndpointVolume;
use windows::Win32::Media::Audio::{
    eCapture, eMultimedia, eRender, EDataFlow, IMMDevice, IMMDeviceEnumerator, MMDeviceEnumerator,
    DEVICE_STATE_ACTIVE,
};
use windows::Win32::System::Com::StructuredStorage::{
    PropVariantClear, PropVariantToString, PROPVARIANT,
};
use windows::Win32::System::Com::{
    CoCreateInstance, CoInitializeEx, CoTaskMemFree, CoUninitialize, CLSCTX_ALL,
    COINIT_MULTITHREADED, STGM_READ,
};
use windows::Win32::UI::Shell::PropertiesSystem::IPropertyStore;

pub(crate) struct ComApartment;

impl ComApartment {
    pub(crate) fn enter() -> Result<Self, String> {
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

unsafe fn endpoint_id(device: &IMMDevice) -> Result<String, String> {
    let id = device.GetId().map_err(|error| error.to_string())?;
    let value = id.to_string().map_err(|error| error.to_string());
    CoTaskMemFree(Some(id.0.cast()));
    value
}

fn endpoint_name(device: &IMMDevice) -> Result<String, String> {
    let store: IPropertyStore =
        unsafe { device.OpenPropertyStore(STGM_READ) }.map_err(|error| error.to_string())?;
    let mut value: PROPVARIANT =
        unsafe { store.GetValue(&PKEY_Device_FriendlyName) }.map_err(|error| error.to_string())?;
    let mut buffer = [0_u16; 512];
    let result =
        unsafe { PropVariantToString(&value, &mut buffer) }.map_err(|error| error.to_string());
    unsafe { PropVariantClear(&mut value) }.map_err(|error| error.to_string())?;
    result?;
    let length = buffer
        .iter()
        .position(|unit| *unit == 0)
        .unwrap_or(buffer.len());
    Ok(String::from_utf16_lossy(&buffer[..length]))
}

pub fn enumerate() -> Result<Vec<Output>, String> {
    let _apartment = ComApartment::enter()?;
    let enumerator: IMMDeviceEnumerator =
        unsafe { CoCreateInstance(&MMDeviceEnumerator, None, CLSCTX_ALL) }
            .map_err(|error| error.to_string())?;
    let current = unsafe { enumerator.GetDefaultAudioEndpoint(eRender, eMultimedia) }
        .ok()
        .and_then(|device| unsafe { endpoint_id(&device).ok() });
    let devices = unsafe { enumerator.EnumAudioEndpoints(eRender, DEVICE_STATE_ACTIVE) }
        .map_err(|error| error.to_string())?;
    let count = unsafe { devices.GetCount() }.map_err(|error| error.to_string())?;
    let mut outputs = Vec::with_capacity(count as usize);
    for index in 0..count {
        let device = unsafe { devices.Item(index) }.map_err(|error| error.to_string())?;
        let Ok(id) = (unsafe { endpoint_id(&device) }) else {
            continue;
        };
        let Ok(name) = endpoint_name(&device) else {
            continue;
        };
        if !name.trim().is_empty() {
            outputs.push(Output {
                is_default: current.as_deref() == Some(id.as_str()),
                id,
                name,
            });
        }
    }
    outputs.sort_by(|left, right| {
        right
            .is_default
            .cmp(&left.is_default)
            .then_with(|| left.name.to_lowercase().cmp(&right.name.to_lowercase()))
    });
    Ok(outputs)
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

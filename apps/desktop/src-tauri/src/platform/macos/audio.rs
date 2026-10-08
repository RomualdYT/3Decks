//! CoreAudio device enumeration and endpoint controls.
use crate::platform::audio::Output;
use std::{
    ffi::{c_char, c_void, CStr},
    mem, ptr,
};

const fn code(value: &[u8; 4]) -> u32 {
    u32::from_be_bytes(*value)
}
const GLOBAL: u32 = code(b"glob");
const OUTPUT: u32 = code(b"outp");
const INPUT: u32 = code(b"inpt");
const DEVICES: u32 = code(b"dev#");
const DEFAULT: u32 = code(b"dOut");
const DEFAULT_INPUT: u32 = code(b"dIn ");
const VOLUME: u32 = code(b"volm");
const VIRTUAL_MAIN_VOLUME: u32 = code(b"vmvc");
const MUTE: u32 = code(b"mute");
const NAME: u32 = code(b"lnam");
const STREAMS: u32 = code(b"stm#");
const UTF8: u32 = 0x0800_0100;
const SYSTEM: u32 = 1;

#[derive(Clone, Copy)]
#[repr(C)]
struct Address {
    selector: u32,
    scope: u32,
    element: u32,
}

impl Address {
    fn new(selector: u32, scope: u32) -> Self {
        Self {
            selector,
            scope,
            element: 0,
        }
    }
    fn channel(selector: u32, scope: u32, element: u32) -> Self {
        Self {
            selector,
            scope,
            element,
        }
    }
}

#[link(name = "CoreAudio", kind = "framework")]
unsafe extern "C" {
    fn AudioObjectGetPropertyDataSize(
        object: u32,
        address: *const Address,
        qualifier_size: u32,
        qualifier: *const c_void,
        size: *mut u32,
    ) -> i32;
    fn AudioObjectGetPropertyData(
        object: u32,
        address: *const Address,
        qualifier_size: u32,
        qualifier: *const c_void,
        size: *mut u32,
        data: *mut c_void,
    ) -> i32;
    fn AudioObjectSetPropertyData(
        object: u32,
        address: *const Address,
        qualifier_size: u32,
        qualifier: *const c_void,
        size: u32,
        data: *const c_void,
    ) -> i32;
}
#[link(name = "CoreFoundation", kind = "framework")]
unsafe extern "C" {
    fn CFStringGetCString(
        value: *const c_void,
        buffer: *mut c_char,
        size: isize,
        encoding: u32,
    ) -> bool;
    fn CFStringGetLength(value: *const c_void) -> isize;
    fn CFStringGetMaximumSizeForEncoding(length: isize, encoding: u32) -> isize;
    fn CFRelease(value: *const c_void);
}

fn size(object: u32, selector: u32, scope: u32) -> Result<u32, String> {
    let mut bytes = 0;
    let status = unsafe {
        AudioObjectGetPropertyDataSize(
            object,
            &Address::new(selector, scope),
            0,
            ptr::null(),
            &mut bytes,
        )
    };
    if status == 0 {
        Ok(bytes)
    } else {
        Err(format!("CoreAudio property size failed: {status}"))
    }
}

fn read_u32(object: u32, selector: u32) -> Result<u32, String> {
    let mut bytes = 4;
    let mut value = 0_u32;
    let status = unsafe {
        AudioObjectGetPropertyData(
            object,
            &Address::new(selector, GLOBAL),
            0,
            ptr::null(),
            &mut bytes,
            (&mut value as *mut u32).cast(),
        )
    };
    if status == 0 && bytes == 4 {
        Ok(value)
    } else {
        Err(format!("CoreAudio property read failed: {status}"))
    }
}

fn read_property<T: Copy + Default>(object: u32, address: Address) -> Result<T, String> {
    let mut bytes = mem::size_of::<T>() as u32;
    let mut value = T::default();
    let status = unsafe {
        AudioObjectGetPropertyData(
            object,
            &address,
            0,
            ptr::null(),
            &mut bytes,
            (&mut value as *mut T).cast(),
        )
    };
    if status == 0 && bytes == mem::size_of::<T>() as u32 {
        Ok(value)
    } else {
        Err(format!("CoreAudio property read failed: {status}"))
    }
}

fn write_property<T: Copy>(object: u32, address: Address, value: T) -> Result<(), String> {
    let status = unsafe {
        AudioObjectSetPropertyData(
            object,
            &address,
            0,
            ptr::null(),
            mem::size_of::<T>() as u32,
            (&value as *const T).cast(),
        )
    };
    if status == 0 {
        Ok(())
    } else {
        Err(format!("CoreAudio property write failed: {status}"))
    }
}

fn volume_addresses(scope: u32) -> [Address; 4] {
    [
        Address::new(VIRTUAL_MAIN_VOLUME, scope),
        Address::new(VOLUME, scope),
        Address::channel(VOLUME, scope, 1),
        Address::channel(VOLUME, scope, 2),
    ]
}

fn read_volume(device: u32, scope: u32) -> Result<u8, String> {
    volume_addresses(scope)
        .into_iter()
        .find_map(|address| read_property::<f32>(device, address).ok())
        .map(|value| (value.clamp(0.0, 1.0) * 100.0).round() as u8)
        .ok_or("This audio device does not expose a volume control".into())
}

fn write_volume(device: u32, scope: u32, value: u8) -> Result<(), String> {
    let scalar = f32::from(value) / 100.0;
    let addresses = volume_addresses(scope);
    for address in addresses[..2].iter().copied() {
        if read_property::<f32>(device, address).is_ok()
            && write_property(device, address, scalar).is_ok()
        {
            return Ok(());
        }
    }
    let mut written = false;
    for address in addresses[2..].iter().copied() {
        if read_property::<f32>(device, address).is_ok() {
            write_property(device, address, scalar)?;
            written = true;
        }
    }
    if written {
        Ok(())
    } else {
        Err("This audio device does not expose a writable volume control".into())
    }
}

pub(crate) fn output_state() -> Result<(u8, bool), String> {
    let device = read_u32(SYSTEM, DEFAULT)?;
    let volume = read_volume(device, OUTPUT)?;
    let muted = read_property::<u32>(device, Address::new(MUTE, OUTPUT))
        .or_else(|_| read_property::<u32>(device, Address::channel(MUTE, OUTPUT, 1)))
        .unwrap_or(0)
        != 0;
    Ok((volume, muted))
}

pub(crate) fn input_volume() -> Result<u8, String> {
    read_volume(read_u32(SYSTEM, DEFAULT_INPUT)?, INPUT)
}

pub(crate) fn set_output_volume(value: u8) -> Result<(), String> {
    write_volume(read_u32(SYSTEM, DEFAULT)?, OUTPUT, value)
}

pub(crate) fn set_output_muted(value: bool) -> Result<(), String> {
    let device = read_u32(SYSTEM, DEFAULT)?;
    if write_property(device, Address::new(MUTE, OUTPUT), u32::from(value)).is_ok() {
        return Ok(());
    }
    let mut written = false;
    for channel in [1, 2] {
        let address = Address::channel(MUTE, OUTPUT, channel);
        if read_property::<u32>(device, address).is_ok() {
            write_property(device, address, u32::from(value))?;
            written = true;
        }
    }
    if written {
        Ok(())
    } else {
        Err("This audio device does not expose a mute control".into())
    }
}

pub(crate) fn set_input_volume(value: u8) -> Result<(), String> {
    write_volume(read_u32(SYSTEM, DEFAULT_INPUT)?, INPUT, value)
}

fn name(id: u32) -> Result<String, String> {
    let mut bytes = mem::size_of::<*const c_void>() as u32;
    let mut reference: *const c_void = ptr::null();
    let status = unsafe {
        AudioObjectGetPropertyData(
            id,
            &Address::new(NAME, GLOBAL),
            0,
            ptr::null(),
            &mut bytes,
            (&mut reference as *mut *const c_void).cast(),
        )
    };
    if status != 0 || reference.is_null() {
        return Err(format!("CoreAudio device name failed: {status}"));
    }
    let result = unsafe {
        let length = CFStringGetLength(reference);
        let capacity = CFStringGetMaximumSizeForEncoding(length, UTF8).saturating_add(1);
        if !(1..=16_384).contains(&capacity) {
            CFRelease(reference);
            return Err("Invalid audio device name length".into());
        }
        let mut buffer = vec![0_i8; capacity as usize];
        let success = CFStringGetCString(reference, buffer.as_mut_ptr(), capacity, UTF8);
        CFRelease(reference);
        if !success {
            Err("Cannot decode audio device name".into())
        } else {
            Ok(CStr::from_ptr(buffer.as_ptr())
                .to_string_lossy()
                .into_owned())
        }
    };
    result
}

pub(crate) fn enumerate() -> Result<Vec<Output>, String> {
    let bytes = size(SYSTEM, DEVICES, GLOBAL)?;
    if bytes == 0 {
        return Ok(Vec::new());
    }
    if bytes > 4096 || bytes % 4 != 0 {
        return Err("Invalid CoreAudio device list size".into());
    }
    let mut ids = vec![0_u32; bytes as usize / 4];
    let mut received = bytes;
    let status = unsafe {
        AudioObjectGetPropertyData(
            SYSTEM,
            &Address::new(DEVICES, GLOBAL),
            0,
            ptr::null(),
            &mut received,
            ids.as_mut_ptr().cast(),
        )
    };
    if status != 0 {
        return Err(format!("CoreAudio device list failed: {status}"));
    }
    if received > bytes || received % 4 != 0 {
        return Err("Invalid CoreAudio device list response".into());
    }
    let current = read_u32(SYSTEM, DEFAULT)?;
    let mut outputs = Vec::new();
    for id in ids.into_iter().take(received as usize / 4) {
        if size(id, STREAMS, OUTPUT).unwrap_or(0) == 0 {
            continue;
        }
        if let Ok(name) = name(id) {
            if !name.is_empty() {
                outputs.push(Output {
                    id: id.to_string(),
                    name,
                    is_default: id == current,
                });
            }
        }
    }
    Ok(outputs)
}

pub(crate) fn set_default(id: &str) -> Result<(), String> {
    let id = id
        .parse::<u32>()
        .map_err(|_| "Invalid CoreAudio device identifier")?;
    let status = unsafe {
        AudioObjectSetPropertyData(
            SYSTEM,
            &Address::new(DEFAULT, GLOBAL),
            0,
            ptr::null(),
            4,
            (&id as *const u32).cast(),
        )
    };
    if status == 0 {
        Ok(())
    } else {
        Err(format!("CoreAudio output switch failed: {status}"))
    }
}

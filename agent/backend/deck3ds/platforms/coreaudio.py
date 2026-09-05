"""Accès aux périphériques de sortie audio de macOS.

L'interface CoreAudio est appelée directement par `ctypes` : aucun outil
externe n'est requis, là où la plupart des solutions imposent d'installer un
utilitaire tiers.

Ce module se limite volontairement à ce qui est utile ici : énumérer les
sorties, connaître celle qui est active et en changer.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import ctypes
import struct
from dataclasses import dataclass

#: Objet racine représentant le système audio.
_SYSTEM_OBJECT = 1

#: Codes de propriétés, exprimés en « quatre caractères » comme le veut l'API.
def _code(text: str) -> int:
    return struct.unpack(">I", text.encode("ascii"))[0]


_SCOPE_GLOBAL = _code("glob")
_SCOPE_OUTPUT = _code("outp")
_PROP_DEVICES = _code("dev#")
_PROP_DEFAULT_OUTPUT = _code("dOut")
_PROP_NAME = _code("lnam")
_PROP_STREAMS = _code("stm#")

#: Encodage UTF-8 tel que le désigne CoreFoundation.
_CF_UTF8 = 0x08000100


class _Address(ctypes.Structure):
    _fields_ = [
        ("selector", ctypes.c_uint32),
        ("scope", ctypes.c_uint32),
        ("element", ctypes.c_uint32),
    ]


@dataclass
class AudioDevice:
    identifier: int
    name: str
    is_default: bool


class CoreAudio:
    """Enveloppe minimale autour de CoreAudio.

    L'instance reste utilisable même si les bibliothèques sont absentes :
    `available` vaut alors `False` et les méthodes se comportent de façon
    inoffensive, ce qui évite d'avoir à tester la plateforme partout.
    """

    def __init__(self) -> None:
        self.available = False
        self._audio = None
        self._foundation = None

        try:
            self._audio = ctypes.CDLL(
                "/System/Library/Frameworks/CoreAudio.framework/CoreAudio"
            )
            self._foundation = ctypes.CDLL(
                "/System/Library/Frameworks/CoreFoundation.framework/"
                "CoreFoundation"
            )
        except OSError:
            return

        self.available = True

    # --- Accès bas niveau -----------------------------------------------------

    def _property_size(self, obj: int, selector: int, scope: int) -> int:
        address = _Address(selector, scope, 0)
        size = ctypes.c_uint32(0)
        result = self._audio.AudioObjectGetPropertyDataSize(
            ctypes.c_uint32(obj), ctypes.byref(address), 0, None,
            ctypes.byref(size)
        )
        return size.value if result == 0 else 0

    def _device_name(self, device: int) -> str:
        address = _Address(_PROP_NAME, _SCOPE_GLOBAL, 0)
        size = ctypes.c_uint32(ctypes.sizeof(ctypes.c_void_p))
        reference = ctypes.c_void_p()

        result = self._audio.AudioObjectGetPropertyData(
            ctypes.c_uint32(device), ctypes.byref(address), 0, None,
            ctypes.byref(size), ctypes.byref(reference)
        )
        if result != 0 or not reference:
            return ""

        buffer = ctypes.create_string_buffer(256)
        self._foundation.CFStringGetCString(
            reference, buffer, len(buffer), _CF_UTF8
        )
        # L'objet retourné nous appartient : il faut le libérer.
        self._foundation.CFRelease(reference)
        return buffer.value.decode("utf-8", "replace")

    def _has_output(self, device: int) -> bool:
        """Vrai si le périphérique possède au moins un flux de sortie.

        Les micros et entrées ligne apparaissent dans la même liste : ce test
        les écarte.
        """
        return self._property_size(device, _PROP_STREAMS, _SCOPE_OUTPUT) > 0

    # --- Interface publique ---------------------------------------------------

    def default_output(self) -> int | None:
        if not self.available:
            return None

        address = _Address(_PROP_DEFAULT_OUTPUT, _SCOPE_GLOBAL, 0)
        size = ctypes.c_uint32(4)
        value = ctypes.c_uint32(0)

        result = self._audio.AudioObjectGetPropertyData(
            ctypes.c_uint32(_SYSTEM_OBJECT), ctypes.byref(address), 0, None,
            ctypes.byref(size), ctypes.byref(value)
        )
        return value.value if result == 0 else None

    def outputs(self) -> list[AudioDevice]:
        """Liste les sorties disponibles, la sortie active en premier plan."""
        if not self.available:
            return []

        total = self._property_size(_SYSTEM_OBJECT, _PROP_DEVICES, _SCOPE_GLOBAL)
        count = total // 4
        if count <= 0:
            return []

        address = _Address(_PROP_DEVICES, _SCOPE_GLOBAL, 0)
        size = ctypes.c_uint32(total)
        identifiers = (ctypes.c_uint32 * count)()

        result = self._audio.AudioObjectGetPropertyData(
            ctypes.c_uint32(_SYSTEM_OBJECT), ctypes.byref(address), 0, None,
            ctypes.byref(size), identifiers
        )
        if result != 0:
            return []

        current = self.default_output()
        devices: list[AudioDevice] = []

        for identifier in identifiers:
            if not self._has_output(identifier):
                continue
            name = self._device_name(identifier)
            if not name:
                continue
            devices.append(
                AudioDevice(identifier, name, identifier == current)
            )

        return devices

    def set_default_output(self, identifier: int) -> bool:
        if not self.available:
            return False

        address = _Address(_PROP_DEFAULT_OUTPUT, _SCOPE_GLOBAL, 0)
        value = ctypes.c_uint32(identifier)

        result = self._audio.AudioObjectSetPropertyData(
            ctypes.c_uint32(_SYSTEM_OBJECT), ctypes.byref(address), 0, None,
            ctypes.c_uint32(4), ctypes.byref(value)
        )
        return result == 0

    def cycle_output(self) -> str | None:
        """Passe à la sortie suivante. Retourne le nom retenu, ou `None`."""
        devices = self.outputs()
        if len(devices) < 2:
            return None

        position = next(
            (index for index, device in enumerate(devices) if device.is_default),
            -1,
        )
        target = devices[(position + 1) % len(devices)]

        if not self.set_default_output(target.identifier):
            return None
        return target.name

    def select_output(self, needle: str) -> str | None:
        """Active la sortie dont le nom contient `needle`, sans tenir compte de
        la casse. Retourne le nom retenu, ou `None` si aucune ne correspond."""
        wanted = needle.strip().lower()
        if not wanted:
            return None

        for device in self.outputs():
            if wanted in device.name.lower():
                if self.set_default_output(device.identifier):
                    return device.name
                return None
        return None

"""Énumération des fenêtres ouvertes sur macOS.

L'API CoreGraphics est appelée par `ctypes`. Ce choix est délibéré : parcourir
les fenêtres avec AppleScript prend environ sept secondes sur une session
chargée, contre une trentaine de millisecondes ici. Une différence de cet ordre
rend la fonctionnalité utilisable au lieu d'être insupportable.

L'ordre retourné suit la profondeur d'empilement : la fenêtre active vient en
premier.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import ctypes
from dataclasses import dataclass

#: Options de `CGWindowListCopyWindowInfo`.
_ON_SCREEN_ONLY = 1
_EXCLUDE_DESKTOP = 16

#: Encodage attendu par CoreFoundation.
_CF_UTF8 = 0x08000100

#: Type numérique `kCFNumberSInt64Type`.
_CF_INT64 = 4

#: Seules les fenêtres applicatives ordinaires nous intéressent : les autres
#: couches contiennent le Dock, la barre des menus et divers panneaux système.
_NORMAL_LAYER = 0


@dataclass
class Window:
    app: str
    title: str
    pid: int
    number: int

    @property
    def label(self) -> str:
        """Libellé affiché sur la console."""
        return self.title if self.title else self.app


class WindowLister:
    def __init__(self) -> None:
        self.available = False
        self._graphics = None
        self._foundation = None
        self._keys: dict[str, ctypes.c_void_p] = {}

        try:
            self._graphics = ctypes.CDLL(
                "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
            )
            self._foundation = ctypes.CDLL(
                "/System/Library/Frameworks/CoreFoundation.framework/"
                "CoreFoundation"
            )
        except OSError:
            return

        self._declare()
        self.available = True

    def _declare(self) -> None:
        """Fixe les signatures : indispensable sur 64 bits, où les pointeurs ne
        tiennent pas dans le type de retour supposé par défaut."""
        graphics = self._graphics
        foundation = self._foundation

        graphics.CGWindowListCopyWindowInfo.restype = ctypes.c_void_p
        graphics.CGWindowListCopyWindowInfo.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]

        foundation.CFArrayGetCount.restype = ctypes.c_long
        foundation.CFArrayGetCount.argtypes = [ctypes.c_void_p]

        foundation.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
        foundation.CFArrayGetValueAtIndex.argtypes = [
            ctypes.c_void_p,
            ctypes.c_long,
        ]

        foundation.CFDictionaryGetValue.restype = ctypes.c_void_p
        foundation.CFDictionaryGetValue.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]

        foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
        foundation.CFStringCreateWithCString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_uint32,
        ]

        foundation.CFStringGetCString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_uint32,
        ]

        foundation.CFNumberGetValue.argtypes = [
            ctypes.c_void_p,
            ctypes.c_long,
            ctypes.c_void_p,
        ]

        foundation.CFRelease.argtypes = [ctypes.c_void_p]

        for name in (
            "kCGWindowOwnerName",
            "kCGWindowName",
            "kCGWindowLayer",
            "kCGWindowOwnerPID",
            "kCGWindowNumber",
        ):
            self._keys[name] = foundation.CFStringCreateWithCString(
                None, name.encode("ascii"), _CF_UTF8
            )

    def _string(self, reference) -> str:
        if not reference:
            return ""
        buffer = ctypes.create_string_buffer(512)
        if self._foundation.CFStringGetCString(
            reference, buffer, len(buffer), _CF_UTF8
        ):
            return buffer.value.decode("utf-8", "replace")
        return ""

    def _number(self, reference) -> int:
        if not reference:
            return 0
        value = ctypes.c_int64(0)
        self._foundation.CFNumberGetValue(
            reference, _CF_INT64, ctypes.byref(value)
        )
        return value.value

    def list(self, limit: int = 12) -> list[Window]:
        """Fenêtres visibles, la plus en avant d'abord."""
        if not self.available:
            return []

        array = self._graphics.CGWindowListCopyWindowInfo(
            _ON_SCREEN_ONLY | _EXCLUDE_DESKTOP, 0
        )
        if not array:
            return []

        try:
            count = self._foundation.CFArrayGetCount(array)
            windows: list[Window] = []

            for index in range(count):
                entry = self._foundation.CFArrayGetValueAtIndex(array, index)
                if not entry:
                    continue

                layer = self._number(
                    self._foundation.CFDictionaryGetValue(
                        entry, self._keys["kCGWindowLayer"]
                    )
                )
                if layer != _NORMAL_LAYER:
                    continue

                app = self._string(
                    self._foundation.CFDictionaryGetValue(
                        entry, self._keys["kCGWindowOwnerName"]
                    )
                )
                if not app:
                    continue

                title = self._string(
                    self._foundation.CFDictionaryGetValue(
                        entry, self._keys["kCGWindowName"]
                    )
                )
                pid = self._number(
                    self._foundation.CFDictionaryGetValue(
                        entry, self._keys["kCGWindowOwnerPID"]
                    )
                )
                number = self._number(
                    self._foundation.CFDictionaryGetValue(
                        entry, self._keys["kCGWindowNumber"]
                    )
                )

                windows.append(Window(app, title, pid, number))
                if len(windows) >= limit:
                    break

            return windows
        finally:
            # Le tableau nous appartient : il faut le libérer.
            self._foundation.CFRelease(array)

"""Native menu implementation backed by pystray.

The rest of the application only knows :class:`TrayBackend`; importing this
module is therefore the sole place where Pillow, Cocoa or Win32 tray code can
enter the process.
"""

from __future__ import annotations

import threading
import subprocess
import sys
from collections.abc import Callable
from typing import Any
from dataclasses import replace

from .models import DesktopSnapshot, TrayActions
from .translations import translate


class PystrayTray:
    def __init__(self, actions: TrayActions, language: str) -> None:
        import pystray  # type: ignore[import-untyped,import-not-found,unused-ignore]

        self._pystray = pystray
        self.actions = actions
        self.language = language
        self._lock = threading.Lock()
        self._snapshot = DesktopSnapshot()
        self._last_rendered: DesktopSnapshot | None = None
        self._icon = pystray.Icon(
            "3Decks",
            self._render_icon(self._snapshot),
            "3Decks",
            self._build_menu(),
        )

    def _text(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _current(self) -> DesktopSnapshot:
        with self._lock:
            return self._snapshot

    def _available(self, _item: object) -> bool:
        return self._current().phase not in {"starting", "stopping"}

    def _build_menu(self) -> Any:
        item, menu = self._pystray.MenuItem, self._pystray.Menu

        def invoke(action: Callable[[], None]) -> Callable[[object, object], None]:
            def callback(_icon: object, _item: object) -> None:
                action()

            return callback

        quick_settings = menu(
            item(
                self._text("notifications"),
                invoke(lambda: self._toggle_feature("notifications")),
                checked=lambda _: self._feature("notifications"),
                enabled=self._available,
            ),
            item(
                self._text("media"),
                invoke(lambda: self._toggle_feature("media")),
                checked=lambda _: self._feature("media"),
                enabled=self._available,
            ),
            item(
                self._text("windows"),
                invoke(lambda: self._toggle_feature("windows")),
                checked=lambda _: self._feature("windows"),
                enabled=self._available,
            ),
            item(
                self._text("system_stats"),
                invoke(lambda: self._toggle_feature("system_stats")),
                checked=lambda _: self._feature("system_stats"),
                enabled=self._available,
            ),
            item(
                self._text("obs"),
                invoke(self._toggle_obs),
                checked=lambda _: self._current().obs_enabled,
                enabled=self._available,
            ),
        )
        pause_menu = menu(
            item(self._text("pause_15"), invoke(lambda: self.actions.pause(15 * 60))),
            item(self._text("pause_60"), invoke(lambda: self.actions.pause(60 * 60))),
            item(self._text("pause_until"), invoke(lambda: self.actions.pause(None))),
        )
        diagnostics = menu(
            item(
                self._text("open_status"),
                invoke(lambda: self.actions.open_ui("status")),
                enabled=lambda _: self._current().ui_ready,
            ),
            item(
                self._text("copy_address"),
                invoke(self.actions.copy_address),
                enabled=lambda _: bool(self._current().address),
            ),
            item(self._text("open_logs"), invoke(self.actions.open_logs)),
            menu.SEPARATOR,
            item(self._text("restart"), invoke(self.actions.restart)),
        )
        return menu(
            item(self._status_text, None, enabled=False),
            item(
                self._text("open"),
                invoke(self.actions.open_ui),
                default=True,
                enabled=lambda _: self._current().ui_ready,
            ),
            item(
                self._text("connect"),
                invoke(lambda: self.actions.open_ui("settings/connection")),
                visible=lambda _: self._current().client_count == 0,
                enabled=lambda _: self._current().ui_ready,
            ),
            menu.SEPARATOR,
            item(
                self._text("resume"),
                invoke(self.actions.resume),
                visible=lambda _: self._current().paused,
            ),
            item(
                self._text("pause"),
                pause_menu,
                visible=lambda _: not self._current().paused,
                enabled=self._available,
            ),
            item(self._text("quick"), quick_settings),
            menu.SEPARATOR,
            item(
                self._text("autostart"),
                invoke(self.actions.toggle_autostart),
                checked=lambda _: self._current().autostart,
                visible=lambda _: self._current().autostart_supported,
            ),
            item(self._text("diagnostics"), diagnostics),
            item(self._text("updates"), invoke(self.actions.open_updates)),
            menu.SEPARATOR,
            item(self._text("quit"), invoke(self.actions.quit)),
        )

    def _feature(self, name: str) -> bool:
        return self._current().features.get(name, False)

    def _toggle_feature(self, name: str) -> None:
        self.actions.set_feature(name, not self._feature(name))

    def _toggle_obs(self) -> None:
        self.actions.set_obs(not self._current().obs_enabled)

    def _status_text(self, _item: object) -> str:
        snapshot = self._current()
        if snapshot.phase in {"starting", "stopping", "degraded"}:
            return self._text(snapshot.phase)
        if snapshot.paused:
            return self._text("paused")
        if snapshot.client_count == 0:
            return self._text("ready_none")
        if snapshot.client_count == 1:
            return self._text("ready_one")
        return self._text("ready_many", count=snapshot.client_count)

    def _tooltip(self, snapshot: DesktopSnapshot) -> str:
        if snapshot.paused:
            return self._text("tooltip_paused")
        if snapshot.client_count == 0:
            return self._text("tooltip_none")
        if snapshot.client_count == 1:
            return self._text("tooltip_one")
        return self._text("tooltip_many", count=snapshot.client_count)

    @staticmethod
    def _render_icon(snapshot: DesktopSnapshot) -> Any:
        from PIL import Image, ImageDraw

        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        if snapshot.phase == "degraded":
            accent = "#F5A524"
        elif snapshot.paused:
            accent = "#A1A1AA"
        elif snapshot.client_count:
            accent = "#66CB10"
        else:
            accent = "#D4D4D8"

        # A deliberately simple two-screen silhouette survives 16 px Windows
        # rendering and remains recognisable in the macOS menu bar.
        draw.rounded_rectangle((9, 5, 55, 29), radius=5, outline=accent, width=5)
        draw.rounded_rectangle((9, 35, 55, 59), radius=5, outline=accent, width=5)
        draw.line((24, 32, 40, 32), fill=accent, width=4)
        draw.rounded_rectangle((16, 11, 48, 23), radius=2, fill=accent)
        if snapshot.paused:
            draw.rounded_rectangle((24, 41, 29, 53), radius=2, fill=accent)
            draw.rounded_rectangle((35, 41, 40, 53), radius=2, fill=accent)
        else:
            draw.ellipse((27, 42, 37, 52), fill=accent)
        return image

    def run(self, setup: Callable[[], None]) -> None:
        def ready(icon: Any) -> None:
            # pystray only makes an icon visible automatically when no custom
            # setup callback is supplied. Ours starts the agent, so visibility
            # must be explicit and, on macOS, dispatched to Cocoa's main queue.
            self._on_native_thread(lambda: setattr(icon, "visible", True))
            setup()

        self._icon.run(setup=ready)

    @staticmethod
    def _on_native_thread(operation: Callable[[], None]) -> None:
        """Run Cocoa mutations on its main queue; Win32 accepts tray updates.

        Recent macOS versions abort when ``NSStatusItem.setMenu`` is reached
        from pystray's worker callback. ``refresh`` originates from the agent
        asyncio thread, so every AppKit-facing mutation crosses this boundary.
        """

        if (
            sys.platform == "darwin"
            and threading.current_thread() is not threading.main_thread()
        ):
            from PyObjCTools import AppHelper  # type: ignore[import-untyped]

            AppHelper.callAfter(operation)
            return
        operation()

    def stop(self) -> None:
        self._on_native_thread(self._icon.stop)

    def refresh(self, snapshot: DesktopSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot
            rendered = replace(snapshot, pause_remaining=None)
            if rendered == self._last_rendered:
                return
            self._last_rendered = rendered

        def apply() -> None:
            self._icon.title = self._tooltip(snapshot)
            self._icon.icon = self._render_icon(snapshot)
            try:
                self._icon.update_menu()
            except RuntimeError:
                # The first snapshot may arrive just before the native menu loop.
                pass

        self._on_native_thread(apply)

    def notify(self, title: str, message: str) -> None:
        def apply() -> None:
            try:
                self._icon.notify(message, title)
            except (OSError, RuntimeError, subprocess.SubprocessError):
                pass

        self._on_native_thread(apply)

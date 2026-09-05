"""Thread-safe bridge between a native tray loop and ``AgentRuntime``."""

from __future__ import annotations

import asyncio
import signal
import subprocess
import sys
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ..feature_catalog import FEATURE_SPECS
from ..runtime.agent import AgentRuntime
from ..runtime.signals import run_agent
from . import system
from .autostart import AutoStart, create_autostart
from .instance import InstanceLock
from .models import DesktopSnapshot, LaunchSpec, TrayBackend
from .translations import preferred_language, translate


@dataclass(frozen=True)
class DesktopOptions:
    launch: LaunchSpec
    log_path: Path
    open_browser: bool = True
    language: str = ""


class DesktopController:
    """Own the background asyncio loop; expose only non-blocking menu calls."""

    def __init__(
        self,
        runtime: AgentRuntime,
        options: DesktopOptions,
        autostart: AutoStart,
        instance: InstanceLock | None = None,
    ) -> None:
        self.runtime, self.options, self.autostart = runtime, options, autostart
        self.language = options.language or preferred_language()
        self.instance = instance
        self.backend: TrayBackend | None = None
        self._snapshot = DesktopSnapshot(
            features={
                name: getattr(runtime.config.features, name) for name in FEATURE_SPECS
            },
            obs_enabled=runtime.config.obs.enabled,
            autostart=autostart.enabled(),
            autostart_supported=autostart.supported,
        )
        self._snapshot_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._background_slots = threading.BoundedSemaphore(4)
        self._ui_url = ""
        self._fatal_error: BaseException | None = None
        self.restart_requested = False

    def attach(self, backend: TrayBackend) -> None:
        self.backend = backend
        backend.refresh(self.snapshot())

    def snapshot(self) -> DesktopSnapshot:
        with self._snapshot_lock:
            return self._snapshot

    def _replace_snapshot(self, snapshot: DesktopSnapshot) -> None:
        with self._snapshot_lock:
            self._snapshot = snapshot
        if self.backend is not None:
            self.backend.refresh(snapshot)

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._thread_main,
            name="3decks-runtime",
            daemon=False,
        )
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    @property
    def started(self) -> bool:
        return self._thread is not None

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._serve())
        except BaseException as error:
            self._fatal_error = error
            self._notify_error(error)
        finally:
            if self.backend is not None:
                self.backend.stop()

    async def _serve(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.runtime.on_ui_ready = self._ui_ready
        if self._stop_requested.is_set():
            self.runtime.request_stop()
        monitor = asyncio.create_task(self._monitor(), name="desktop-status")
        try:
            await run_agent(self.runtime)
        finally:
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)
            await self._capture("stopping")

    async def _monitor(self) -> None:
        while True:
            if self.instance is not None and self.instance.stop_requested():
                self.quit()
            self.runtime.expire_controls_pause()
            await self._capture()
            await asyncio.sleep(0.75)

    async def _capture(self, forced_phase: str = "") -> None:
        health = self.runtime.health()
        if forced_phase:
            phase = forced_phase
        elif health.get("components", {}).get("tcp") == "starting":
            phase = "starting"
        else:
            phase = str(health["status"])
        clients = len(self.runtime.client_summaries())
        addresses = self.runtime.local_addresses()
        address = addresses[0] if addresses else f"127.0.0.1:{self.runtime.config.port}"
        paused = self.runtime.controls_paused
        remaining = self.runtime.controls_pause_remaining
        snapshot = DesktopSnapshot(
            phase=phase,
            client_count=clients,
            address=address,
            ui_ready=bool(self._ui_url),
            paused=paused,
            pause_remaining=remaining,
            features={
                name: getattr(self.runtime.config.features, name)
                for name in FEATURE_SPECS
            },
            obs_enabled=self.runtime.config.obs.enabled,
            autostart=self.autostart.enabled(),
            autostart_supported=self.autostart.supported,
        )
        self._replace_snapshot(snapshot)

    def _ui_ready(self, url: str) -> None:
        self._ui_url = url
        if self.instance is not None:
            self.instance.publish_url(url)
        if self.options.open_browser:
            system.open_url(url)

    def _destination_url(self, destination: str) -> str:
        return self._ui_url + (f"#{destination}" if destination else "")

    def _notify_error(self, error: BaseException) -> None:
        if self.backend is not None:
            message = str(error).strip() or translate(self.language, "error")
            self.backend.notify("3Decks", message)

    def _submit(self, operation: Callable[[], Awaitable[Any]]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            self._notify_error(RuntimeError(translate(self.language, "error")))
            return

        async def invoke() -> None:
            await operation()
            await self._capture()

        future = asyncio.run_coroutine_threadsafe(invoke(), loop)

        def completed(result: Future[None]) -> None:
            try:
                result.result()
            except BaseException as error:
                self._notify_error(error)

        future.add_done_callback(completed)

    def _background(self, operation: Callable[[], None]) -> None:
        if not self._background_slots.acquire(blocking=False):
            return

        def run() -> None:
            try:
                operation()
            except BaseException as error:
                self._notify_error(error)
            finally:
                self._background_slots.release()

        try:
            threading.Thread(target=run, name="3decks-desktop-action", daemon=True).start()
        except RuntimeError as error:
            self._background_slots.release()
            self._notify_error(error)

    def open_ui(self, destination: str = "") -> None:
        url = self._destination_url(destination)
        if url:
            self._background(lambda: system.open_url(url))

    def pause(self, seconds: int | None) -> None:
        async def apply() -> None:
            self.runtime.pause_controls(seconds)

        self._submit(apply)

    def resume(self) -> None:
        async def apply() -> None:
            self.runtime.resume_controls()

        self._submit(apply)

    def set_feature(self, name: str, enabled: bool) -> None:
        async def apply() -> None:
            changes = {name: enabled}
            await self.runtime.services.config.update_runtime_settings(features=changes)

        self._submit(apply)

    def set_obs(self, enabled: bool) -> None:
        async def apply() -> None:
            await self.runtime.services.config.update_runtime_settings(
                obs_enabled=enabled
            )

        self._submit(apply)

    def toggle_autostart(self) -> None:
        def apply() -> None:
            self.autostart.set_enabled(not self.autostart.enabled())
            current = self.snapshot()
            self._replace_snapshot(replace(current, autostart=self.autostart.enabled()))

        self._background(apply)

    def copy_address(self) -> None:
        address = self.snapshot().address

        def apply() -> None:
            system.copy_text(address)
            if self.backend is not None:
                self.backend.notify("3Decks", translate(self.language, "copied"))

        self._background(apply)

    def open_logs(self) -> None:
        self._background(lambda: system.open_path(self.options.log_path))

    def open_updates(self) -> None:
        self._background(lambda: system.open_url(system.RELEASES_URL))

    def restart(self) -> None:
        self.restart_requested = True
        self.quit()

    def quit(self) -> None:
        self._stop_requested.set()
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self.runtime.request_stop)

    @property
    def failed(self) -> bool:
        return self._fatal_error is not None


def _launch_detached(spec: LaunchSpec) -> None:
    options: dict[str, Any] = {
        "cwd": spec.working_directory,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform in {"win32", "cygwin"}:
        options["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        ) | getattr(subprocess, "DETACHED_PROCESS", 0)
    else:
        options["start_new_session"] = True
    subprocess.Popen(spec.command(), **options)


def run_desktop(runtime: AgentRuntime, options: DesktopOptions) -> int:
    """Run the tray on the main thread and the agent on one asyncio worker."""

    from .tray import PystrayTray

    instance = InstanceLock.for_config(runtime.config_path)
    if not instance.acquire():
        try:
            url = instance.existing_url()
            if url:
                system.open_url(url)
            return 0
        finally:
            # Runtime construction owns native pools even before start(). A
            # second launch hands off to the first process, then releases all
            # resources it has already allocated.
            asyncio.run(runtime.close())

    controller: DesktopController | None = None
    previous: dict[signal.Signals, Any] = {}

    def stop(_signum: int, _frame: object) -> None:
        if controller is not None:
            controller.quit()

    try:
        controller = DesktopController(
            runtime, options, create_autostart(options.launch), instance
        )
        tray = PystrayTray(controller, controller.language)
        controller.attach(tray)
        if threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGINT, signal.SIGTERM):
                previous[signum] = signal.signal(signum, stop)
        tray.run(controller.start)
    finally:
        if controller is not None:
            controller.quit()
            if controller.started:
                # Shutdown drains accepted saves, native operations and
                # extension processes. Do not abandon that ownership merely
                # because a GUI loop has already returned.
                controller.join()
            else:
                asyncio.run(runtime.close())
        else:
            asyncio.run(runtime.close())
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        instance.release()

    assert controller is not None
    if controller.restart_requested and not controller.failed:
        _launch_detached(options.launch)
    return 1 if controller.failed else 0

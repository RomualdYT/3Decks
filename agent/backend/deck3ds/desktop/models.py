"""Small immutable contracts shared by the desktop controller and tray UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable
from typing import Protocol


@dataclass(frozen=True)
class LaunchSpec:
    """Exact command used for login startup and a graceful restart."""

    executable: Path
    arguments: tuple[str, ...]
    working_directory: Path

    def command(self) -> list[str]:
        return [str(self.executable), *self.arguments]


@dataclass(frozen=True)
class DesktopSnapshot:
    """Detached view of the runtime safe to consume from the GUI thread."""

    phase: str = "starting"
    client_count: int = 0
    address: str = ""
    ui_ready: bool = False
    paused: bool = False
    pause_remaining: int | None = None
    features: dict[str, bool] = field(default_factory=dict)
    obs_enabled: bool = False
    autostart: bool = False
    autostart_supported: bool = False


class TrayBackend(Protocol):
    """Platform UI owned by the main thread."""

    def run(self, setup: Callable[[], None]) -> None: ...
    def stop(self) -> None: ...
    def refresh(self, snapshot: DesktopSnapshot) -> None: ...
    def notify(self, title: str, message: str) -> None: ...


class TrayActions(Protocol):
    """Commands exposed by the controller to the native menu."""

    def snapshot(self) -> DesktopSnapshot: ...
    def open_ui(self, destination: str = "") -> None: ...
    def pause(self, seconds: int | None) -> None: ...
    def resume(self) -> None: ...
    def set_feature(self, name: str, enabled: bool) -> None: ...
    def set_obs(self, enabled: bool) -> None: ...
    def toggle_autostart(self) -> None: ...
    def copy_address(self) -> None: ...
    def open_logs(self) -> None: ...
    def open_updates(self) -> None: ...
    def restart(self) -> None: ...
    def quit(self) -> None: ...

"""Login-startup adapters with no dependency on the tray implementation."""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from typing import Protocol

from .models import LaunchSpec


class AutoStart(Protocol):
    @property
    def supported(self) -> bool: ...
    def enabled(self) -> bool: ...
    def set_enabled(self, enabled: bool) -> None: ...


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class MacAutoStart:
    supported = True

    def __init__(self, spec: LaunchSpec, path: Path | None = None) -> None:
        self.spec = spec
        self.path = (
            path or Path.home() / "Library/LaunchAgents/com.romualdyt.3decks.plist"
        )

    def enabled(self) -> bool:
        return self.path.is_file()

    def set_enabled(self, enabled: bool) -> None:
        if not enabled:
            self.path.unlink(missing_ok=True)
            return
        document = {
            "Label": "com.romualdyt.3decks",
            "ProgramArguments": self.spec.command(),
            "WorkingDirectory": str(self.spec.working_directory),
            "RunAtLoad": True,
            "ProcessType": "Interactive",
        }
        _atomic_write(self.path, plistlib.dumps(document, sort_keys=True))


class WindowsAutoStart:
    supported = True

    def __init__(
        self,
        spec: LaunchSpec,
        path: Path | None = None,
        runner: Callable[..., Any] = subprocess.run,
    ) -> None:
        self.spec = spec
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        self.path = (
            path or appdata / "Microsoft/Windows/Start Menu/Programs/Startup/3Decks.lnk"
        )
        self._runner = runner

    def enabled(self) -> bool:
        return self.path.is_file()

    def set_enabled(self, enabled: bool) -> None:
        if not enabled:
            self.path.unlink(missing_ok=True)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        environment = dict(os.environ)
        environment.update(
            {
                "DECK3DS_SHORTCUT": str(self.path),
                "DECK3DS_TARGET": str(self.spec.executable),
                "DECK3DS_ARGUMENTS": subprocess.list2cmdline(self.spec.arguments),
                "DECK3DS_WORKDIR": str(self.spec.working_directory),
            }
        )
        script = (
            "$shell=New-Object -ComObject WScript.Shell;"
            "$link=$shell.CreateShortcut($env:DECK3DS_SHORTCUT);"
            "$link.TargetPath=$env:DECK3DS_TARGET;"
            "$link.Arguments=$env:DECK3DS_ARGUMENTS;"
            "$link.WorkingDirectory=$env:DECK3DS_WORKDIR;"
            "$link.Description='3Decks agent';"
            "$link.Save()"
        )
        completed = self._runner(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            env=environment,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if completed.returncode != 0 or not self.path.is_file():
            raise OSError("Windows could not create the login shortcut")


class UnsupportedAutoStart:
    supported = False

    def enabled(self) -> bool:
        return False

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            raise OSError("Login startup is unavailable on this platform")


def create_autostart(spec: LaunchSpec) -> AutoStart:
    if sys.platform == "darwin":
        return MacAutoStart(spec)
    if sys.platform in {"win32", "cygwin"}:
        return WindowsAutoStart(spec)
    return UnsupportedAutoStart()

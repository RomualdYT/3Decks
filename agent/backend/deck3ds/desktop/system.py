"""Narrow, testable operating-system helpers used by native menu actions."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path


RELEASES_URL = "https://github.com/RomualdYT/3Decks/releases/latest"


def open_url(url: str) -> None:
    if not webbrowser.open(url):
        raise OSError("No browser accepted the URL")


def open_path(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    if sys.platform == "darwin":
        subprocess.Popen(["/usr/bin/open", str(path)])
    elif sys.platform in {"win32", "cygwin"}:
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


def copy_text(value: str) -> None:
    if sys.platform == "darwin":
        command = ["/usr/bin/pbcopy"]
    elif sys.platform in {"win32", "cygwin"}:
        command = [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "$input | Set-Clipboard",
        ]
    else:
        command = ["xclip", "-selection", "clipboard"]
    completed = subprocess.run(
        command,
        input=value,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    if completed.returncode != 0:
        raise OSError("The clipboard command failed")

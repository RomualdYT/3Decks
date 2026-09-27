"""Reject release tags that disagree with desktop package metadata."""

from __future__ import annotations

import json
import re
import runpy
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(tag: str) -> None:
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError(f"Invalid release tag: {tag}")
    expected = tag[1:]
    npm_lock = json.loads((ROOT / "desktop/package-lock.json").read_text())
    cargo_lock = tomllib.loads((ROOT / "desktop/src-tauri/Cargo.lock").read_text())
    locked_desktop = next(package for package in cargo_lock["package"] if package["name"] == "decks-desktop")
    sources = {
        "Tauri": json.loads((ROOT / "desktop/src-tauri/tauri.conf.json").read_text())["version"],
        "npm": json.loads((ROOT / "desktop/package.json").read_text())["version"],
        "npm lock": npm_lock["version"],
        "npm lock root": npm_lock["packages"][""]["version"],
        "Cargo": tomllib.loads((ROOT / "desktop/src-tauri/Cargo.toml").read_text())["package"]["version"],
        "Cargo lock": locked_desktop["version"],
    }
    for name, actual in sources.items():
        if actual != expected:
            raise ValueError(f"{name} version {actual} does not match {tag}")
    runpy.run_path(str(ROOT / "packaging/3ds/package_version.py"), run_name="release_version_check")["encode"](tag)


if __name__ == "__main__":
    try:
        check(sys.argv[1])
    except (IndexError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Release version {sys.argv[1]} matches desktop metadata.")

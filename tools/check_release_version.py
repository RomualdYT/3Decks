"""Check release metadata and matching JavaScript/Rust Tauri dependencies."""

from __future__ import annotations

import json
import re
import runpy
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_tauri_versions(npm_lock: dict, cargo_lock: dict) -> None:
    for npm_name in npm_lock["packages"][""]["dependencies"]:
        if npm_name == "@tauri-apps/api":
            crate_name = "tauri"
        elif npm_name.startswith("@tauri-apps/plugin-"):
            crate_name = npm_name.replace("@tauri-apps/", "tauri-")
        else:
            continue
        npm_version = npm_lock["packages"][f"node_modules/{npm_name}"]["version"]
        crate_versions = [
            package["version"] for package in cargo_lock["package"]
            if package["name"] == crate_name
        ]
        if not crate_versions or any(
            version.split(".")[:2] != npm_version.split(".")[:2]
            for version in crate_versions
        ):
            raise ValueError(
                f"Tauri version mismatch: {npm_name} {npm_version}, "
                f"{crate_name} {', '.join(crate_versions) or 'missing'}. "
                "Align their major/minor versions and update both lockfiles."
            )


def check(tag: str) -> None:
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError(f"Invalid release tag: {tag}")
    expected = tag[1:]
    npm_lock = json.loads((ROOT / "apps/desktop/package-lock.json").read_text())
    cargo_lock = tomllib.loads((ROOT / "apps/desktop/src-tauri/Cargo.lock").read_text())
    locked_desktop = next(package for package in cargo_lock["package"] if package["name"] == "decks-desktop")
    sources = {
        "Tauri": json.loads((ROOT / "apps/desktop/src-tauri/tauri.conf.json").read_text())["version"],
        "npm": json.loads((ROOT / "apps/desktop/package.json").read_text())["version"],
        "npm lock": npm_lock["version"],
        "npm lock root": npm_lock["packages"][""]["version"],
        "Cargo": tomllib.loads((ROOT / "apps/desktop/src-tauri/Cargo.toml").read_text())["package"]["version"],
        "Cargo lock": locked_desktop["version"],
    }
    for name, actual in sources.items():
        if actual != expected:
            raise ValueError(f"{name} version {actual} does not match {tag}")
    check_tauri_versions(npm_lock, cargo_lock)
    runpy.run_path(str(ROOT / "apps/console/packaging/package_version.py"), run_name="release_version_check")["encode"](tag)


if __name__ == "__main__":
    try:
        check(sys.argv[1])
    except (IndexError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Release version {sys.argv[1]} matches desktop metadata and Tauri dependencies.")

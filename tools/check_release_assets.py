"""Validate a draft release before attaching its checksum manifest."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

REQUIRED_PLATFORMS = {"darwin-aarch64", "darwin-x86_64", "windows-x86_64"}
REQUIRED_CONSOLE = {"deck3ds.3dsx", "deck3ds.cia"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(directory: Path) -> None:
    files = {path.name: path for path in directory.iterdir() if path.is_file()}
    missing = (REQUIRED_CONSOLE | {"latest.json"}) - files.keys()
    if missing:
        raise ValueError(f"Missing release assets: {', '.join(sorted(missing))}")
    manifest = json.loads(files["latest.json"].read_text())
    tag = os.environ.get("RELEASE_TAG") or os.environ.get("GITHUB_REF_NAME")
    if tag and str(manifest.get("version", "")).lstrip("v") != tag.lstrip("v"):
        raise ValueError(f"Updater version does not match {tag}")
    platforms = manifest.get("platforms", {})
    for target in REQUIRED_PLATFORMS:
        entries = [value for key, value in platforms.items() if target in key]
        if not entries:
            raise ValueError(f"Updater manifest lacks {target}")
        for entry in entries:
            if not entry.get("signature") or not entry.get("url"):
                raise ValueError(f"Updater manifest has incomplete {target} entry")
            asset = Path(unquote(urlsplit(entry["url"]).path)).name
            # Draft updater manifests use GitHub asset API URLs ending in an ID.
            # Resolve those through the matching detached signature, not the ID.
            if asset not in files and urlsplit(entry["url"]).hostname == "api.github.com":
                matches = [
                    name.removesuffix(".sig") for name, path in files.items()
                    if name.endswith(".sig")
                    and path.read_text().strip() == entry["signature"].strip()
                ]
                if len(matches) != 1:
                    raise ValueError(f"Cannot resolve updater asset for {target}")
                asset = matches[0]
            if asset not in files:
                raise ValueError(f"Updater package missing: {asset}")
            if asset + ".sig" not in files:
                raise ValueError(f"Updater signature missing: {asset}.sig")
            if files[asset + ".sig"].read_text().strip() != entry["signature"].strip():
                raise ValueError(f"Updater signature does not match manifest: {asset}")
    if not any(name.endswith(".dmg") for name in files):
        raise ValueError("Missing macOS DMG")
    if not any(name.endswith((".msi", "-setup.exe")) for name in files):
        raise ValueError("Missing Windows installer")
    checksums = directory / "SHA256SUMS.txt"
    checksums.write_text("".join(
        f"{sha256(path)}  {name}\n"
        for name, path in sorted(files.items()) if name != checksums.name
    ))


if __name__ == "__main__":
    try:
        check(Path(sys.argv[1]))
    except (IndexError, ValueError) as error:
        raise SystemExit(str(error)) from error

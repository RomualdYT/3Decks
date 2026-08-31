"""Dependency-free author tooling. Validation and packaging never execute code."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from .manifest import ExtensionError, ID, load_manifest
from .packages import MAX_ARCHIVE_BYTES, fingerprint, package_files

STARTER = '''"""3Decks extension: customize this file, then validate and package it."""
from deck3ds.extensions.sdk import Extension, Result, Snapshot

extension = Extension()
count = 0


@extension.initialize
def initialize(context):
    global count
    count = context.load(default={}).get("count", 0)


@extension.action("increment")
def increment(context, arguments):
    global count
    count += arguments["amount"]
    context.save({"count": count})
    return Result(message=str(count))


@extension.poll
def poll(context):
    return Snapshot(dashboards={"counter": {
        "title": context.settings["title"],
        "status": "ok",
        "cards": [{"label": {"en": "Count", "fr": "Compteur"}, "value": str(count)}],
    }})


if __name__ == "__main__":
    extension.serve()
'''


def create(destination: Path, identifier: str) -> Path:
    if not ID.fullmatch(identifier):
        raise ExtensionError(
            "Invalid id; use a lowercase reverse-domain id, e.g. com.example.counter"
        )
    if destination.exists():
        raise ExtensionError("Destination already exists; no files were changed")
    manifest = {
        "api_version": 1,
        "id": identifier,
        "version": "1.0.0",
        "name": {"en": "My counter", "fr": "Mon compteur"},
        "description": {
            "en": "A starting point for your own integration.",
            "fr": "Une base pour votre propre intégration.",
        },
        "author": "Your name",
        "runtime": "python",
        "entrypoint": "main.py",
        "platforms": ["darwin", "win32", "linux"],
        "permissions": ["filesystem"],
        "poll_interval": 1,
        "settings": [
            {
                "name": "title",
                "label": {"en": "Screen title", "fr": "Titre de l’écran"},
                "type": "text",
                "default": "My counter",
                "required": True,
            }
        ],
        "actions": [
            {
                "id": "increment",
                "title": {"en": "Increment", "fr": "Incrémenter"},
                "icon": "plus",
                "color": "#66CB10",
                "arguments": [
                    {
                        "name": "amount",
                        "type": "number",
                        "label": {"en": "Amount", "fr": "Quantité"},
                        "default": 1,
                        "min": 1,
                        "max": 100,
                    }
                ],
            }
        ],
        "dashboards": [
            {
                "id": "counter",
                "title": {"en": "My counter", "fr": "Mon compteur"},
                "icon": "monitor",
            }
        ],
    }
    destination.mkdir(parents=True)
    (destination / "extension.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "main.py").write_text(STARTER, encoding="utf-8")
    (destination / "README.md").write_text(
        "# My 3Decks extension\n\nEdit extension.json and main.py. No dependencies required.\n\n"
        "From the agent directory, run `python -m deck3ds.extensions validate PATH`, then "
        "`python -m deck3ds.extensions pack PATH -o counter.3deckext`. "
        "Import the package from Extensions in the UI, review it, enable it, then add its action and top screen.\n\n"
        "Author guide: docs/EXTENSIONS.md in the 3Decks repository. Choose a license before distributing.\n",
        encoding="utf-8",
    )
    return destination


def pack(package: Path, destination: Path) -> str:
    package, destination = package.resolve(), destination.resolve()
    if package == destination or package in destination.parents:
        raise ExtensionError("Write the archive outside the source package")
    load_manifest(package / "extension.json")
    digest = fingerprint(package)
    files = package_files(package)
    if destination.exists():
        raise ExtensionError("Output already exists; choose a new filename")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.relative_to(package).as_posix())
    if destination.stat().st_size > MAX_ARCHIVE_BYTES:
        # Only this invocation's new artifact is removed, never a user's file.
        destination.unlink()
        raise ExtensionError("Compressed archive exceeds 4 MiB; output removed")
    return digest

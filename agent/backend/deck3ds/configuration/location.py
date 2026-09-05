"""Source checkout compatibility and explicit, non-destructive first-run setup."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from platformdirs import user_config_path

from .serialization import to_raw
from .validation import parse


def default_config_path() -> Path:
    source_root = Path(__file__).resolve().parents[3]
    legacy = source_root / "config.json"
    if (source_root / "frontend").is_dir() and legacy.is_file():
        return legacy
    return user_config_path("3Decks", appauthor=False) / "config.json"


def initialize(path: Path) -> None:
    """Create a neutral configuration exclusively; never replace an existing file."""
    document = to_raw(
        parse(
            {
                "server": {"token": secrets.token_urlsafe(32)},
                "pages": [
                    {
                        "id": "main",
                        "title": {"en": "Main", "fr": "Principal"},
                        "icon": "star",
                        "dashboard": "auto",
                        "buttons": [
                            {
                                "id": "quieter",
                                "slot": 0,
                                "label": {"en": "Quieter", "fr": "Moins fort"},
                                "action": "volume.down",
                            },
                            {
                                "id": "louder",
                                "slot": 1,
                                "label": {"en": "Louder", "fr": "Plus fort"},
                                "action": "volume.up",
                            },
                            {
                                "id": "play",
                                "slot": 2,
                                "label": {
                                    "en": "Play / pause",
                                    "fr": "Lecture / pause",
                                },
                                "action": "media.play_pause",
                            },
                        ],
                    }
                ],
            }
        )
    )
    encoded = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise

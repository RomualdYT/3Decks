"""Atomic UTF-8 configuration storage, with unique same-directory temporaries."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
from pathlib import Path

from .models import Config, ConfigError
from .serialization import to_raw
from .validation import parse


def save(config: Config, path: Path) -> str:
    raw = to_raw(config)
    parse(raw)
    text = json.dumps(raw, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load(path: Path) -> Config:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ConfigError(f"fichier introuvable: {path}") from error
    except OSError as error:
        raise ConfigError(f"lecture impossible: {error}") from error
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"JSON invalide ligne {error.lineno}, colonne {error.colno}: {error.msg}"
        ) from error
    return parse(raw)

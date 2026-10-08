"""Inject the repository's updater public key into Tauri's release overlay."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "apps/desktop/src-tauri/tauri.release.conf.json"


def prepare(output: Path, public_key: str) -> None:
    key = public_key.strip()
    if not key:
        raise ValueError("Missing updater public key: DECKS_UPDATER_PUBKEY")
    try:
        lines = base64.b64decode(key, validate=True).decode("utf-8").splitlines()
        raw_key = base64.b64decode(lines[1], validate=True)
        if not lines[0].startswith("untrusted comment:") or len(raw_key) != 42 or raw_key[:2] != b"Ed":
            raise ValueError("Invalid Minisign public key")
    except (ValueError, IndexError) as error:
        raise ValueError("Invalid updater public key: use the contents of the Tauri .pub file") from error
    config = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    config.setdefault("plugins", {}).setdefault("updater", {})["pubkey"] = key
    output.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=TEMPLATE)
    args = parser.parse_args()
    try:
        prepare(args.output, os.environ.get("DECKS_UPDATER_PUBKEY", ""))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print("Release updater configuration prepared.")

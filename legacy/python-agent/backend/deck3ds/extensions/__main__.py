"""Run with python -m deck3ds.extensions (from agent/ in a source checkout)."""

from __future__ import annotations

import argparse
from pathlib import Path

from .manifest import ExtensionError, load_manifest
from .packages import fingerprint
from .scaffold import create, pack


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Create, validate and package 3Decks extensions (no code execution)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    starter = commands.add_parser(
        "init", help="Create a working Python counter extension"
    )
    starter.add_argument("path", type=Path)
    starter.add_argument("--id", required=True)
    check = commands.add_parser(
        "validate", help="Validate manifest, package limits and fingerprint"
    )
    check.add_argument("path", type=Path)
    archive = commands.add_parser("pack", help="Create an installable .3deckext ZIP")
    archive.add_argument("path", type=Path)
    archive.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            print(f"Created {create(args.path, args.id)}")
        elif args.command == "validate":
            manifest = load_manifest(args.path / "extension.json")
            print(
                f"Valid: {manifest['id']} v{manifest['version']} (API 1)\nSHA-256: {fingerprint(args.path)}"
            )
        else:
            print(f"SHA-256: {pack(args.path, args.output)}\nPackage: {args.output}")
    except (ExtensionError, OSError, ValueError) as error:
        parser.exit(1, f"Extension error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Deterministic OpenAPI export; no runtime or native adapter is constructed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .app import create_app


def specification() -> str:
    return (
        json.dumps(create_app().openapi(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = specification()
    if args.check:
        if args.output is None:
            parser.error("--check requires an output path")
        if (
            not args.output.exists()
            or args.output.read_text(encoding="utf-8") != document
        ):
            print(
                "OpenAPI is stale. Regenerate the specification and TypeScript types.",
                file=sys.stderr,
            )
            return 1
    elif args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(document, encoding="utf-8")
    else:
        print(document, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

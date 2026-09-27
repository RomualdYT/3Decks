"""Check the public sample (optionally its reachable Git history), without secrets in output."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

SECRET_KEYS = {"token", "password", "secret", "api_key", "access_token", "refresh_token"}
PERSONAL_PATH = re.compile(r"/Users/|[A-Za-z]:[\\/]Users[\\/]", re.IGNORECASE)


def issues(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in SECRET_KEYS and child:
                found.add("nonempty credential")
            found.update(issues(child))
    elif isinstance(value, list):
        for child in value:
            found.update(issues(child))
    elif isinstance(value, str) and PERSONAL_PATH.search(value):
        found.add("personal profile path")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    target = "agent/config.json"
    documents = [("working tree", (root / target).read_bytes())]
    if args.history:
        revisions = subprocess.check_output(
            ["git", "log", "--all", "--format=%H", "--", target], cwd=root, text=True
        ).splitlines()
        for revision in revisions:
            documents.append((revision[:12], subprocess.check_output(
                ["git", "show", f"{revision}:{target}"], cwd=root
            )))
    failures = 0
    for label, raw in documents:
        try:
            problems = issues(json.loads(raw))
        except (ValueError, UnicodeError):
            problems = {"invalid JSON"}
        if problems:
            failures += 1
            print(f"{label}: {', '.join(sorted(problems))}")
    print(f"Public configuration: {len(documents)} documents checked; {failures} failed.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())

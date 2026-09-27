"""Check local links and heading anchors in the maintained documentation.

No network access, dependencies or file modifications. External URLs and code
examples are deliberately excluded; this is not a complete Markdown parser.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")
HTML_LINK = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
REFERENCE = re.compile(r"^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)


def prose(source: str) -> str:
    lines: list[str] = []
    fence = ""
    for line in source.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if not fence:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = ""
            continue
        if not fence:
            lines.append(line)
    return "\n".join(lines)


def anchors(source: str) -> set[str]:
    result = set(re.findall(r"""\bid=["']([^"']+)["']""", prose(source)))
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", prose(source), re.MULTILINE):
        heading = re.sub(r"<[^>]+>", "", heading).lower()
        heading = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", heading)
        slug = "".join(c for c in heading if c.isalnum() or c in " _-").replace(
            " ", "-"
        )
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def check(path: Path, root: Path = ROOT) -> list[str]:
    source = prose(path.read_text(encoding="utf-8"))
    targets = [
        *LINK.findall(source),
        *HTML_LINK.findall(source),
        *REFERENCE.findall(source),
    ]
    failures = []
    for target in targets:
        target = target.strip("<>")
        url = urlsplit(target)
        if url.scheme or url.netloc:
            continue
        location = unquote(url.path)
        resolved = (
            (
                root / location.lstrip("/")
                if location.startswith("/")
                else path.parent / location
            )
            if location
            else path
        )
        if not resolved.exists():
            failures.append(f"{path.relative_to(root)}: missing target {target}")
        elif (
            url.fragment
            and resolved.is_file()
            and resolved.suffix == ".md"
            and unquote(url.fragment)
            not in anchors(resolved.read_text(encoding="utf-8"))
        ):
            failures.append(f"{path.relative_to(root)}: missing heading {target}")
    return failures


def documents(root: Path = ROOT) -> list[Path]:
    files = set(root.glob("*.md"))
    for directory in ("docs", "packaging", "examples"):
        files.update((root / directory).rglob("*.md"))
    files.update((root / "desktop").glob("*.md"))
    files.update((root / "desktop/docs").glob("*.md"))
    files.update((root / "desktop/extension-sdk").glob("*.md"))
    return sorted(files)


def main() -> int:
    files = documents()
    failures = [failure for path in files for failure in check(path)]
    for failure in failures:
        print(failure, file=sys.stderr)
    print(
        f"Documentation: {len(files)} files checked, {len(failures)} broken local links."
    )
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())

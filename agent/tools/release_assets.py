"""Render immutable, checksummed GitHub Release assets from one wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import struct
import zipfile
from email.parser import Parser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "packaging" / "launchers"
DEFAULT_ICON = ROOT / "agent" / "frontend" / "public" / "3decks-logo.png"
REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
TAG_PATTERN = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wheel_version(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        metadata = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("wheel must contain exactly one METADATA file")
        message = Parser().parsestr(archive.read(metadata[0]).decode("utf-8"))
    version = message.get("Version", "")
    if not version:
        raise ValueError("wheel metadata has no Version")
    return version


def png_ico(png: bytes) -> bytes:
    """Wrap one PNG as a standards-compliant Vista+ ICO without image tooling."""
    if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
        raise ValueError("release icon is not a PNG")
    width, height = struct.unpack(">II", png[16:24])
    if not (1 <= width <= 256 and 1 <= height <= 256):
        raise ValueError("PNG icon dimensions must be between 1 and 256 pixels")
    width_byte = 0 if width == 256 else width
    height_byte = 0 if height == 256 else height
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack(
        "<BBBBHHII", width_byte, height_byte, 0, 0, 1, 32, len(png), 22
    )
    return header + entry + png


def _render(template: Path, values: dict[str, str], target: Path) -> None:
    content = template.read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace(f"__{key}__", value)
    leftovers = sorted(set(re.findall(r"__[A-Z0-9_]+__", content)))
    if leftovers:
        raise ValueError(f"unresolved launcher placeholders: {', '.join(leftovers)}")
    target.write_text(content, encoding="utf-8", newline="\n")


def render(
    *,
    wheel: Path,
    output: Path,
    repository: str,
    tag: str,
    icon: Path = DEFAULT_ICON,
    source_archive: Path | None = None,
) -> dict[str, object]:
    wheel = wheel.resolve(strict=True)
    icon = icon.resolve(strict=True)
    if REPOSITORY_PATTERN.fullmatch(repository) is None:
        raise ValueError("repository must use the owner/name form")
    if TAG_PATTERN.fullmatch(tag) is None:
        raise ValueError("release tag must use the vMAJOR.MINOR.PATCH form")
    version = wheel_version(wheel)
    if tag != f"v{version}":
        raise ValueError(f"tag {tag!r} does not match wheel version {version!r}")

    output.mkdir(parents=True, exist_ok=True)
    copied_wheel = output / wheel.name
    shutil.copyfile(wheel, copied_wheel)
    copied_icon = output / "3decks-logo.png"
    shutil.copyfile(icon, copied_icon)
    windows_icon = output / "3decks.ico"
    windows_icon.write_bytes(png_ico(icon.read_bytes()))
    if source_archive is not None:
        shutil.copyfile(source_archive.resolve(strict=True), output / source_archive.name)

    values = {
        "REPOSITORY": repository,
        "RELEASE_TAG": tag,
        "VERSION": version,
        "WHEEL_NAME": wheel.name,
        "WHEEL_SHA256": sha256(copied_wheel),
        "ICON_SHA256": sha256(copied_icon),
        "WINDOWS_ICON_SHA256": sha256(windows_icon),
    }
    macos = output / "install-3decks-macos.sh"
    windows = output / "install-3decks-windows.ps1"
    _render(TEMPLATES / f"{macos.name}.in", values, macos)
    _render(TEMPLATES / f"{windows.name}.in", values, windows)
    macos.chmod(macos.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    manifest: dict[str, object] = {
        "schema": 1,
        "name": "3Decks",
        "version": version,
        "tag": tag,
        "repository": repository,
        "wheel": {"name": wheel.name, "sha256": values["WHEEL_SHA256"]},
        "installers": {
            "macos": macos.name,
            "windows": windows.name,
        },
    }
    (output / "release.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    checksummed = sorted(
        path
        for path in output.iterdir()
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in checksummed),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--icon", type=Path, default=DEFAULT_ICON)
    parser.add_argument("--source-archive", type=Path)
    args = parser.parse_args()
    manifest = render(
        wheel=args.wheel,
        output=args.output,
        repository=args.repository,
        tag=args.tag,
        icon=args.icon,
        source_archive=args.source_archive,
    )
    print(f"Rendered release assets for {manifest['tag']} in {args.output}")


if __name__ == "__main__":
    main()

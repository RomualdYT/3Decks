"""Check HOME packages against the built icon, banner, font and ELF's SVC usage.

These structural checks do not replace installation and launch on real hardware.
Uses only the Python standard library; no personal console data is accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/console"
TITLE_ID = 0x000400000F3D3C00


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def align64(value: int) -> int:
    return (value + 63) & ~63


def check_ncch(data: bytes) -> None:
    require(data[0x100:0x104] == b"NCCH", "Missing executable NCCH")
    require(struct.unpack_from("<Q", data, 0x118)[0] == TITLE_ID, "Wrong title ID")
    require(data[0x18F] & 4 != 0, "Homebrew NCCH must be unencrypted")
    require(hashlib.sha256(data[0x200:0x600]).digest() == data[0x160:0x180],
            "Extended header checksum mismatch")
    exefs_offset = u32(data, 0x1A0) * 512
    exefs_size = u32(data, 0x1A4) * 512
    require(exefs_offset + exefs_size <= len(data), "Truncated ExeFS")
    exefs = data[exefs_offset:exefs_offset + exefs_size]
    entries = {}
    for index in range(8):
        name, offset, size = struct.unpack_from("<8sII", exefs, index * 16)
        if not name.strip(b"\0"):
            continue
        name = name.rstrip(b"\0").decode("ascii")
        content = exefs[512 + offset:512 + offset + size]
        require(len(content) == size, f"Truncated {name}")
        expected = exefs[0x100 + (7 - index) * 32:0x120 + (7 - index) * 32]
        require(hashlib.sha256(content).digest() == expected, f"Invalid {name} hash")
        entries[name] = content
    require(entries.get("icon") == (APP / "deck3ds.smdh").read_bytes(), "Wrong icon")
    icon = entries["icon"]
    require(len(icon) == 0x36C0 and icon[:4] == b"SMDH", "Invalid HOME icon metadata")
    for language in (1, 2):  # English and French title slots.
        title = icon[8 + language * 512:8 + language * 512 + 128]
        require(title.decode("utf-16-le").rstrip("\0") == "3Decks", "Wrong HOME title")
    require(u32(icon, 0x2028) & 1 != 0, "Application is hidden on HOME")
    require(u32(icon, 0x2018) & 0x7F == 0x7F, "Unexpected region restriction")
    require(entries.get("banner") == (APP / "build/banner.bnr").read_bytes(), "Wrong banner")
    require(bool(entries.get(".code")), "Missing application code")
    romfs_offset = u32(data, 0x1B0) * 512
    romfs_size = u32(data, 0x1B4) * 512
    require(romfs_offset > 0 and romfs_offset + romfs_size <= len(data), "Invalid RomFS")
    fonts = [APP / "romfs/deck.bcfnt", *sorted((APP / "romfs/fonts").glob("*.bcfnt"))]
    require(len(fonts) == 7, "Expected fallback and six native font sizes")
    for font in fonts:
        require(font.read_bytes() in data[romfs_offset:romfs_offset + romfs_size],
                f"Bundled Inter console font missing: {font.name}")
    icon_sizes = [int(value) for value in re.findall(
        r"^ICON_SIZE\((\d+)\)$",
        (APP / "source/graphics/icon_sizes.def").read_text(), re.MULTILINE)]
    require(bool(icon_sizes), "Missing console icon sizes")
    for size in icon_sizes:
        atlas = APP / f"romfs/icons/icons-{size}.t3x"
        require(atlas.read_bytes() in data[romfs_offset:romfs_offset + romfs_size],
                f"Bundled icon atlas missing: {atlas.name}")
    spotify = APP / "romfs/brands/spotify.t3x"
    require(spotify.read_bytes() in data[romfs_offset:romfs_offset + romfs_size],
            "Bundled Spotify mark missing")


def check_cia(data: bytes) -> None:
    require(u32(data, 0) == 0x2020, "Invalid CIA header")
    offset = align64(u32(data, 0))
    for size_offset in (8, 12, 16):
        offset = align64(offset + u32(data, size_offset))
    content_size = struct.unpack_from("<Q", data, 24)[0]
    require(content_size > 512 and offset + content_size <= len(data), "Truncated CIA content")
    check_ncch(data[offset:offset + content_size])


def check_syscalls(objdump: str) -> None:
    disassembly = subprocess.check_output([objdump, "-d", str(APP / "deck3ds.elf")], text=True)
    used = {int(value, 16) for value in re.findall(r"\bsvc\s+0x([0-9a-fA-F]+)", disassembly)}
    rsf = (ROOT / "apps/console/packaging/application.rsf").read_text()
    section = rsf.split("SystemCallAccess:", 1)[1].split("ServiceAccessControl:", 1)[0]
    allowed = {int(value) for value in re.findall(r":\s+(\d+)\s*$", section, re.MULTILINE)}
    require(bool(used), "No ELF system calls detected; check objdump format")
    require(used <= allowed, f"Missing kernel permissions: {sorted(used - allowed)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objdump")
    args = parser.parse_args()
    check_cia((APP / "deck3ds.cia").read_bytes())
    if args.objdump:
        check_syscalls(args.objdump)
    print("Console packaging (CIA): identity, hashes, fonts and icons OK")


if __name__ == "__main__":
    main()

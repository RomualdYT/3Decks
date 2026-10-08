#!/usr/bin/env python3
"""Generate the native-size BCFNT family inside the devkitPro container."""
import pathlib
import re
import struct
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "apps/console"
MANIFEST = APP / "source/graphics/font_faces.def"


def main():
    faces = re.findall(r"^FONT_FACE\((\w+), (\d+), ([\d.]+)\)$", MANIFEST.read_text(), re.M)
    if len(faces) != 6:
        raise SystemExit("Expected six font styles in font_faces.def")
    output = APP / "romfs/fonts"
    # Stage everything so a failed conversion cannot leave a mixed family.
    with tempfile.TemporaryDirectory() as directory:
        staged = []
        for style, height, points in faces:
            path = pathlib.Path(directory) / f"deck-{height}.bcfnt"
            subprocess.run([
                "/opt/devkitpro/tools/bin/mkbcfnt", "-s", points,
                "-w", str(ROOT / "tools/font-charset.txt"), "-o", str(path),
                str(ROOT / "tools/fonts/Inter-Regular.ttf"),
            ], check=True, stdout=subprocess.DEVNULL)
            data = path.read_bytes()
            # CFNT header (20), FINF's TGLP pointer (16), points past block header.
            tglp = struct.unpack_from("<I", data, 20 + 16)[0]
            actual = data[tglp + 1]
            if actual != int(height):
                raise SystemExit(f"{style}: expected {height}px cell, got {actual}px")
            staged.append((path.name, data))
            print(f"{style}: {height}px native, {len(data)} bytes", flush=True)
        output.mkdir(parents=True, exist_ok=True)
        for name, data in staged:
            (output / name).write_bytes(data)


if __name__ == "__main__":
    main()

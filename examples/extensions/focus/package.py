#!/usr/bin/env python3
"""Build and package Focus for one supported Rust target using only stdlib."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
TARGETS = {
    "aarch64-apple-darwin": "darwin-aarch64",
    "x86_64-apple-darwin": "darwin-x86_64",
    "aarch64-pc-windows-msvc": "win32-aarch64",
    "x86_64-pc-windows-msvc": "win32-x86_64",
    "aarch64-unknown-linux-gnu": "linux-aarch64",
    "x86_64-unknown-linux-gnu": "linux-x86_64",
}


def executable(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    candidate = Path.home() / ".cargo" / "bin" / (name + (".exe" if os.name == "nt" else ""))
    if candidate.is_file():
        return str(candidate)
    raise RuntimeError(f"{name} is required; install the Rust toolchain first")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, help="Rust target (defaults to this host)")
    parser.add_argument("--output", type=Path, help="Destination .3deckext file")
    args = parser.parse_args()
    target = args.target
    if target is None:
        version = subprocess.check_output([executable("rustc"), "-vV"], text=True)
        target = next(line.removeprefix("host: ") for line in version.splitlines() if line.startswith("host: "))
    if target not in TARGETS:
        parser.error(f"Unsupported target: {target}")
    subprocess.run([
        executable("cargo"), "build", "--release", "--locked", "--target", target,
        "--manifest-path", str(ROOT / "Cargo.toml"), "--target-dir", str(ROOT / "target"),
    ], check=True)

    manifest = json.loads((ROOT / "extension.template.json").read_text(encoding="utf-8"))
    binary_name = "focus.exe" if TARGETS[target].startswith("win32-") else "focus"
    binary = ROOT / "target" / target / "release" / binary_name
    manifest["binaries"] = {TARGETS[target]: f"bin/{binary_name}"}
    output = args.output or ROOT / "dist" / f"focus-{manifest['version']}-{TARGETS[target]}.3deckext"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("extension.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            executable_entry = zipfile.ZipInfo(f"bin/{binary_name}")
            executable_entry.create_system = 3
            executable_entry.external_attr = 0o100755 << 16
            executable_entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(executable_entry, binary.read_bytes())
            for name in ("README.md", "README.fr.md"):
                archive.write(ROOT / name, name)
            if sum(entry.file_size for entry in archive.infolist()) > 16 * 1024 * 1024:
                raise RuntimeError("Focus exceeds the host's 16 MiB unpacked limit")
        if temporary.stat().st_size > 4 * 1024 * 1024:
            raise RuntimeError("Focus exceeds the host's 4 MiB archive limit")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error

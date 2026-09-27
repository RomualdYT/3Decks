"""Safe package storage: no installation hooks, bounded ZIPs, atomic registry."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

from .manifest import ExtensionError, load_manifest

MAX_FILES = 256
MAX_PACKAGE_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024


def portable_path(value: str) -> PurePosixPath:
    """Reject aliases/devices that behave differently on Windows and POSIX."""
    path = PurePosixPath(value)
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if (
        not path.parts
        or path.is_absolute()
        or any(
            part in (".", "..")
            or part.endswith((".", " "))
            or part.split(".")[0].upper() in reserved
            or any(char in '<>:"\\|?*' or ord(char) < 32 for char in part)
            for part in path.parts
        )
    ):
        raise ExtensionError("Unsafe or non-portable package path")
    return path


def package_files(root: Path) -> list[Path]:
    files = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ExtensionError("Symbolic links are not allowed in extension packages")
        portable_path(path.relative_to(root).as_posix())
        if path.is_file():
            files.append(path)
            total += path.stat().st_size
            if len(files) > MAX_FILES or total > MAX_PACKAGE_BYTES:
                raise ExtensionError("Package exceeds 256 files or 16 MiB")
    return files


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in package_files(root):
        name = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        # Length-prefix both components; file contents may contain NUL bytes.
        digest.update(len(name).to_bytes(4, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def write_private_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("object expected")
        return value
    except (OSError, ValueError) as error:
        raise ExtensionError(
            f"Cannot read {path.name}; existing file was preserved"
        ) from error


def install_archive(archive: Path, root: Path) -> str:
    """Install a new package, disabled. Never replace an existing package."""
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ExtensionError("Archive exceeds 4 MiB")
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".install-", dir=root) as temporary:
        staging = Path(temporary)
        try:
            with zipfile.ZipFile(archive) as bundle:
                entries = bundle.infolist()
                if (
                    len(entries) > MAX_FILES
                    or sum(item.file_size for item in entries) > MAX_PACKAGE_BYTES
                ):
                    raise ExtensionError(
                        "Archive exceeds 256 entries or 16 MiB unpacked"
                    )
                names = set()
                for item in entries:
                    name = portable_path(item.filename)
                    mode = item.external_attr >> 16
                    if (
                        name.is_absolute()
                        or ".." in name.parts
                        or "\\" in item.filename
                        or ":" in item.filename
                        or stat.S_ISLNK(mode)
                        or item.filename.casefold() in names
                        or item.flag_bits & 1
                    ):
                        raise ExtensionError(
                            "Unsafe, duplicate or encrypted archive entry"
                        )
                    names.add(item.filename.casefold())
                    target = staging.joinpath(*name.parts)
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with bundle.open(item) as source, target.open("wb") as output:
                            shutil.copyfileobj(source, output)
                        # Preserve only executable bits, never special modes.
                        if mode & 0o111:
                            target.chmod(0o700)
        except (zipfile.BadZipFile, OSError, RuntimeError) as error:
            raise ExtensionError("Invalid extension archive") from error
        manifest = load_manifest(staging / "extension.json")
        fingerprint(staging)
        destination = root / "packages" / manifest["id"]
        if destination.exists():
            raise ExtensionError(
                "Already installed: remove the old package before importing an update (settings are kept)"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(destination)
        return manifest["id"]


def retire_package(package: Path, root: Path) -> Path:
    """Recoverable removal. Persistent settings/data are intentionally retained."""
    destination = root / "trash" / f"{package.name}-{time.time_ns()}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    package.rename(destination)
    return destination

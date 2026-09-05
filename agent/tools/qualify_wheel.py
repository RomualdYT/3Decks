"""Audit a wheel and qualify a locked, Node-free installation outside the repo."""

from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def audit(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        entry_points = [
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        ]
        assert len(entry_points) == 1
        commands = archive.read(entry_points[0]).decode("utf-8")
    for required in (
        "deck3ds/api/static/index.html",
        "deck3ds/__main__.py",
        "deck3ds/desktop/application.py",
        "deck3ds/extensions/sdk.py",
    ):
        assert required in names, required
    assert any(name.endswith(".woff2") for name in names)
    assert any(name.endswith("device-shell.png") for name in names)
    assert any(name.endswith("Inter-OFL.txt") for name in names)
    assert any("licenses/LICENSE" in name for name in names)
    assert "deck3ds = deck3ds.__main__:main" in commands
    assert "deck3ds-ui = deck3ds.__main__:ui_main" in commands
    for name in names:
        parts = Path(name).parts
        assert "config.json" not in parts and "registry.json" not in parts, name
        assert not set(parts) & {"__pycache__", "node_modules", ".venv", ".git"}, name
        assert not name.endswith((".pyc", ".map")), name
        assert not name.startswith(("deck3ds/ui/", "deck3ds/srv/")), name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path, nargs="?")
    parser.add_argument("--uv", default=shutil.which("uv"))
    args = parser.parse_args()
    if not args.uv:
        parser.error("uv must be installed or supplied with --uv")
    candidates = [args.wheel] if args.wheel else sorted(Path("dist").glob("*.whl"))
    if len(candidates) != 1:
        parser.error("Pass an exact wheel path, or keep exactly one wheel in dist/")
    wheel = candidates[0].resolve(strict=True)
    audit(wheel)
    project = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="3decks-wheel-") as directory:
        root = Path(directory)
        constraints = root / "runtime.txt"
        subprocess.run(
            [
                args.uv,
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--output-file",
                str(constraints),
            ],
            cwd=project,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [args.uv, "venv", "--python", sys.executable, str(root / "venv")],
            check=True,
        )
        python = (
            root
            / "venv"
            / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        )
        subprocess.run(
            [
                args.uv,
                "pip",
                "install",
                "--python",
                str(python),
                "--constraints",
                str(constraints),
                str(wheel),
            ],
            check=True,
        )
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment["PATH"] = str(python.parent)
        subprocess.run(
            [
                str(python),
                str(project / "tools" / "smoke_installed.py"),
                "--example",
                str(project.parent / "examples" / "extensions" / "focus-timer"),
            ],
            cwd=root,
            env=environment,
            check=True,
        )
        executable_directory = python.parent
        ui_entry = executable_directory / (
            "deck3ds-ui.exe" if sys.platform == "win32" else "deck3ds-ui"
        )
        subprocess.run([str(ui_entry), "--version"], env=environment, check=True)
    print("Wheel contents and locked installation qualified")


if __name__ == "__main__":
    main()

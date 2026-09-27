# Manual Python installation

[Documentation](README.md) · [Français](PYTHON_SETUP.fr.md)

Most users should use the [release launchers](INSTALLATION.md). This guide is for installing a built wheel yourself. For source development and frontend builds, use [Contributing](CONTRIBUTING_AGENT.md).

## Requirements

Python 3.12 or newer and a release wheel. No Node.js is needed to run the packaged editor. These instructions do not assume a PyPI publication.

### macOS

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install /path/to/deck3ds-0.2.0-py3-none-any.whl
.venv/bin/deck3ds-ui
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install C:\Downloads\deck3ds-0.2.0-py3-none-any.whl
.venv\Scripts\deck3ds-ui.exe
```

Replace the example wheel path/version with the artifact you downloaded. The GUI entry creates a configuration only if missing. For a terminal agent, use `deck3ds --ui`; without `--ui`, no editor HTTP listener is started. `python -m deck3ds` also works inside this environment.

## Configuration and permissions

Use `--config PATH` to select an existing configuration. To explicitly create a new one, use `deck3ds --config PATH --init-config`; existing files are never overwritten. Settings and extensions stay outside the program environment. See [storage and backups](CONFIGURATION.md).

macOS permissions belong to the actual executable running the agent. A different Python can require permission again. A wheel installation does **not** supply MSIX identity for Windows notifications.

A normal pip wheel installation resolves dependencies from package metadata. Reproducible source/CI environments use the committed `uv.lock`. The wheel includes editor assets, console PNG and licensed fonts.

## Update and remove

Stop the selected agent before replacing its wheel. Back up the entire configuration directory. Install the desired wheel in the same environment and launch with the same config path. Remove the environment to remove the program; personal data remains in its separate directory. Do not delete that directory unless you intentionally want to erase your settings.

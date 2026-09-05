# Installing and migrating the FastAPI agent

[Documentation](README.md) · [Français](MIGRATION_FASTAPI.fr.md) · [Architecture](ARCHITECTURE.md) · [HTTP reference](api/README.md) · [Contributor guide](CONTRIBUTING_AGENT.md)

For a first installation, prefer [Install 3Decks](INSTALLATION.md). This guide is
for existing configurations and manual Python environments. For a fresh source
checkout, follow [source setup](CONTRIBUTING_AGENT.md) to build frontend assets
and create an ignored private configuration before launching.

## What changes

3Decks 0.2 requires Python **3.12 or newer**. The qualification targets are Python 3.12, 3.13 and 3.14. The agent now uses FastAPI, Pydantic 2, minimal Uvicorn and platformdirs. No database, remote account, Redis, Celery or additional agent process is introduced.

The React editor, console TCP protocol 1, UDP discovery on 38122, extension API 1 and configuration format are retained. `python -m deck3ds` still works; an installed `deck3ds` command is also available. The old HTTP implementation is removed, not kept as a fallback.

## From a source checkout

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```sh
cd agent
uv sync --locked
uv run --locked deck3ds --ui
```

An existing checkout configuration is reused. Do not run an old Python 3.9 virtual environment against this version. `uv sync --locked` creates the supported environment and refuses an inconsistent lockfile.

To choose another existing file:

```sh
uv run --locked deck3ds --config /absolute/path/config.json --ui
```

For a new configuration, explicitly use `--init-config`. It creates bilingual demonstration controls and a fresh durable console token; **it refuses to overwrite any existing file**.

```sh
uv run --locked deck3ds --config config.local.json --init-config
uv run --locked deck3ds --config config.local.json --ui
```

Node.js is required only for frontend contributors/builders, not for running a built agent.

## From a built wheel, outside the repository

Obtain the wheel from a qualified build or the CI `python-distribution` artifact. These instructions do not assume a PyPI publication.

macOS:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install /path/to/deck3ds-0.2.0-py3-none-any.whl
.venv/bin/deck3ds --init-config
.venv/bin/deck3ds --ui
```

Windows PowerShell, without changing the script execution policy:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install C:\Downloads\deck3ds-0.2.0-py3-none-any.whl
.venv\Scripts\deck3ds.exe --init-config
.venv\Scripts\deck3ds.exe --ui
```

The wheel includes the editor, console PNG, icons and Inter fonts. Its resources are local; no Node executable or CDN is needed at runtime. For a reproducible development/release installation, use the committed `uv.lock`; a normal wheel installation resolves compatible dependencies from package metadata. CI qualifies the wheel using constraints exported from the lockfile.

## Configuration selection and migration

Selection order is:

1. The explicit `--config` path.
2. The historical `agent/config.json`, when running from a checkout that contains it.
3. The OS user configuration directory: typically `~/Library/Application Support/3Decks/config.json` on macOS or `%LOCALAPPDATA%\3Decks\config.json` on Windows. `platformdirs` resolves the actual location.

The current directory is not an implicit configuration source in an installed package. Use `--config` when reusing your old file outside the checkout. Extensions remain in `extensions/` **next to that selected file**. Nothing is moved automatically. Keep the extension registry, packages and data with that directory when moving it yourself.

Before upgrading, stop the old agent and back up the selected configuration and adjacent extension directory. Existing console tokens, OBS passwords, scripts, localized names and extension approvals remain valid. On first reconnect, a legacy shared console token is transparently exchanged for an individually revocable credential; back up the newly created adjacent `paired-consoles.json` too. UI links are ephemeral: after restarting, open the new link printed by the agent. The persistent 3DS credential is distinct from this UI session.

HTTP saves are atomic and immediately installed in memory. Another browser save or a detected external file edit returns `409 config_conflict`; reload before editing further. External invalid JSON is not installed. External editors do not participate in the agent's lock: avoid editing the file while saving in the UI. The final operating-system replace is atomic, but arbitrary external writers cannot be made transactional by the agent.

## Platform permissions

macOS permissions remain attached to the application/interpreter that runs the agent. A changed Python executable may need renewed Automation, Accessibility, or Full Disk Access permissions. Use the editor's permission shortcuts, then inspect its status. FastAPI does not bypass OS permissions.

**A Python/pip installation does not provide Windows MSIX identity.** Windows notifications still require MSIX identity, the `userNotificationListener` capability and the user's approval. There is no SQLite fallback. The manual `Windows Store package` workflow wraps the published wheel in an unsigned MSIX intended only for Partner Center; Microsoft signs an accepted Store submission.

Linux runs the portable core/tests; it is not advertised as a newly supported native integration platform.

## Headless mode, diagnostics and rollback

Omit `--ui` to run only console transport/discovery and integrations. `--ui-port` changes the loopback port, never its address. A busy UI port is nonfatal to the console. `--check` validates the selected file; `--probe` performs real native collection and may require permissions. `--verbose` adds diagnostic logs.

For rollback, stop this agent and reinstall the previously qualified artifact/environment. Reuse the same configuration path. There is no inverse data migration and no switch to a legacy HTTP backend. Retain your backup in case an unrelated extension version changed its own data format.

See [qualification and measurements](QUALIFICATION.md) for what was actually tested and what still requires real macOS/Windows hardware verification.

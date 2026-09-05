# 3Decks agent

[Documentation](https://github.com/RomualdYT/3Decks/blob/main/docs/README.md) ·
[Installation](https://github.com/RomualdYT/3Decks/blob/main/docs/INSTALLATION.md) ·
[Français](https://github.com/RomualdYT/3Decks/blob/main/docs/README.fr.md)

A local, extensible macOS/Windows control surface for Nintendo 3DS.
Python 3.12+; FastAPI, Pydantic 2, minimal Uvicorn and platformdirs.

After installing the wheel, `deck3ds --init-config` explicitly creates a neutral
configuration without overwriting an existing file. `deck3ds --ui` starts the
agent and opens its local editor. `python -m deck3ds` is equivalent. Use
`--config PATH` to reuse an existing file; extensions stay beside that file.
The installed `deck3ds-ui` GUI entry creates a first configuration only when it
is missing, then starts the agent and editor without a Windows console window.
On macOS and Windows it also owns the native menu-bar/notification-area item.
That menu exposes connection status, pause/resume, quick integration settings,
diagnostics, login startup, restart and a real Quit action.

The wheel includes React/HeroUI assets, the console PNG and Inter fonts. End users
do not need Node.js. The HTTP editor is loopback-only and optional; the TCP/UDP
console protocols and API 1 extension SDK remain independent of HTTP.

Responsibilities in `deck3ds/`:

- `api/`: HTTP routes, wire models, security and compiled static resources;
- `services/`: configuration transactions, per-console credentials and editor/system/extension operations;
- `configuration/`: models, shared validation, serialization and atomic storage;
- `runtime/`: native factory, composition, supervision, signals and shutdown;
- `desktop/`: thread-safe native menu host, single-instance handoff, login startup and durable GUI logs;
- `transports/`: console TCP, discovery UDP and publication;
- `platforms/`: native macOS and Windows integrations;
- `extensions/`: framework-independent API 1 SDK and approved extension processes.

From a source checkout's `agent/`, run `uv sync --locked`, then
follow the contributor guide to build frontend assets and select a private
configuration. Use `deck3ds-ui` for the native menu or `deck3ds --ui` for a
terminal agent with browser UI. The small `agent/deck3ds/` shim preserves source
imports. `uv build` produces a source archive and wheel; full migration,
architecture, API, contribution and qualification guides are in repository `docs/`.

Windows notifications require MSIX identity, the declared notification capability
and user approval. Installing Python/the wheel alone does not provide that
identity. No SQLite fallback exists. `backend/windows/` retains installer metadata;
the manual Store workflow packages the published wheel for Partner Center, which
signs an accepted submission. Linux qualifies the portable core only.

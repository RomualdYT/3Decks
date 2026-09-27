# Desktop architecture

The native desktop application lives in [`desktop/`](../desktop/README.md). Its Tauri window loads the same React editor source as `frontend/`. The editor uses one typed API boundary; the entry point selects `desktop/src/tauri-api.ts` for Tauri or the isolated HTTP adapter for historical preview builds. React does not start Python or call the archived HTTP server in the desktop bundle.

| Layer | Code | Responsibility |
|---|---|---|
| UI | `frontend/src/` | Editor, settings, pages, shared types and components |
| Desktop bridge | `desktop/src/` | Onboarding, Tauri command adapter and desktop styling |
| Application state | `desktop/src-tauri/src/app/` | Configuration, credentials, pairing, tray and lifecycle |
| Transport | `desktop/src-tauri/src/transport/` | UDP discovery, framed TCP, 3DS protocol |
| Features | `desktop/src-tauri/src/features/` | Media, lyrics, OBS, telemetry, extensions and notifications |
| Platform adapters | `desktop/src-tauri/src/platform/` | macOS, Windows and Linux system integration |
| Console | `3ds-app/source/` | Native C UI and network client |

The Rust server runs on Tokio tasks independently of the WebView. Closing the editor keeps the server and tray active. Configuration changes use a revision and are broadcast to connected consoles. App pairing credentials are stored in the application config directory; the pre-release `.poc` application ID is migrated on first launch under the final ID.

The archived Python implementation, historical HTTP API and distribution scripts are in [`legacy/python-agent/`](../legacy/python-agent/README.md). The current [3DS protocol](PROTOCOL.md) is the shared wire contract.

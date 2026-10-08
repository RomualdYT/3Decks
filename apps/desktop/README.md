# 3Decks desktop

Tauri 2/Rust application with a shared React/HeroUI editor. Start with
[installation](../../docs/INSTALLATION.md) or [usage](../../docs/USAGE.md).

## Features and platform support

The app provides console pairing, a visual editor, settings, a system tray/menu,
media and audio controls, application/window shortcuts, telemetry, OBS and native
extensions. Optional synchronized lyrics use LRCLIB or local LRC files.
The [platform matrix](PLATFORM_STATUS.md) describes OS-specific availability.

Closing the editor destroys its WebView while leaving the server running.
Use **Open 3Decks** in the system menu to recreate the window, or **Quit** to stop
it. Configuration, pairing, onboarding progress and extension data are stored
in the application's local configuration directory.

## Development

Install Rust stable, Node.js 24, pnpm 11 and the
[Tauri platform prerequisites](https://v2.tauri.app/start/prerequisites/).
The Rust crates use edition 2024.

From the repository root:

```sh
cd apps/desktop/frontend
pnpm install --frozen-lockfile
cd ..
npm ci
npm run tauri -- dev
```

Build a local application from `apps/desktop/`:

```sh
npm run tauri -- build
```

Local builds do not configure distribution signing or updater keys by default.
See [release maintenance](../../docs/RELEASE.md) for published packages and
[contributor checks](../../docs/CONTRIBUTING.md) before opening a pull request.

## Source map

| Path | Responsibility |
| --- | --- |
| `frontend/` | Shared editor, settings, extension views and generated API types |
| `src/` | Desktop React entry point, onboarding and Tauri command adapter |
| `src-tauri/src/app/` | Configuration, pairing, lifecycle, tray and persistence |
| `src-tauri/src/transport/` | Console discovery, TCP framing and sessions |
| `src-tauri/src/features/` | Artwork, lyrics, notifications, OBS, telemetry and extensions |
| `src-tauri/src/platform/` | macOS, Windows and Linux system adapters |
| `catalog.json`, `default-config.json` | Bundled editor catalog and initial configuration |
| [extension-sdk](extension-sdk/README.md) | Native extension author API |

The [architecture guide](../../docs/ARCHITECTURE.md) explains these boundaries.
Update the catalog alongside native action implementations; the running app
resolves availability from the platform and enabled features.

## Development environment variables

| Variable | Effect |
| --- | --- |
| `DECKS_TCP_PORT` | Override the default TCP control port, 38123 |
| `DECKS_DISCOVERY_PORT` | Override the default UDP discovery port, 38122 |
| `DECKS_START_TRAY_ONLY=1` | Start without opening the editor |
| `DECKS_TEST_PAIR_CODE` | Fixed initial pairing code in debug builds only; ignored in release |
| `DECKS_UPDATER_PUBKEY` | Embed the updater public key at compile time |

Only one listener can bind a given port. Automatic console discovery uses UDP
38122; with alternate development ports, use the console's manual IP/TCP setup.

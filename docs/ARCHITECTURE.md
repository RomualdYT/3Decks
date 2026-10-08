# Desktop architecture

[Documentation](README.md) · [Français](ARCHITECTURE.fr.md)

3Decks has two programs: the Tauri desktop application and the C client on the 3DS. The desktop process owns the local network server, system integrations, configuration and tray. Its WebView runs the React editor; closing that window keeps the desktop process and console connection alive.

## Source map

| Area | Responsibility |
|---|---|
| [`apps/desktop/frontend/src/`](../apps/desktop/frontend/src/) | Editor, settings, localization, shared components and generated API types |
| [`apps/desktop/shell/`](../apps/desktop/shell/) | Tauri entry point, onboarding, command adapter and desktop styles |
| [`apps/desktop/src-tauri/src/app/`](../apps/desktop/src-tauri/src/app/) | Persistent configuration, pairing, onboarding progress, window lifecycle and tray |
| [`apps/desktop/src-tauri/src/transport/`](../apps/desktop/src-tauri/src/transport/) | UDP discovery, framed TCP sessions and 3DS messages |
| [`apps/desktop/src-tauri/src/features/`](../apps/desktop/src-tauri/src/features/) | OBS, lyrics, artwork, telemetry, notifications and native extensions |
| [`apps/desktop/src-tauri/src/platform/`](../apps/desktop/src-tauri/src/platform/) | OS specific audio, keyboard, media, windows and shell adapters |
| [`apps/console/source/`](../apps/console/source/) | Console UI, input, networking and protocol parser |

The editor calls a typed boundary in `apps/desktop/frontend/src/api/client.ts`. The desktop build resolves that boundary to `apps/desktop/shell/tauri-api.ts`, which invokes Rust commands. The frontend HTTP adapter is isolated for development of the shared editor; it is excluded from the desktop bundle. New desktop features should extend the Rust command adapter and its types instead of adding HTTP calls to React components.

## Console connection and state

1. The desktop starts Tokio tasks for UDP discovery on port 38122 and the TCP listener on port 38123. Neither runs on the WebView thread.
2. The console discovers the computer or uses a manually entered address. TCP messages contain a four-byte big-endian JSON length followed by the JSON payload. The [protocol guide](PROTOCOL.md) defines limits and message types.
3. A new console pairs with the six-digit code shown in the app. The desktop stores a digest of the per-console credential in its configuration directory; a known console reconnects with its credential.
4. The desktop validates actions, invokes the relevant feature or platform adapter, and sends state and results back to the console. Saving a page increments the configuration revision and broadcasts the new layout to connected consoles.

The network is intended for a trusted LAN. The transport is not encrypted; see [Security](SECURITY.md). The application config and onboarding progress are stored separately. The setup assistant resumes its saved step after a restart.

## Platform boundaries

Shared control flow belongs in `features/` or `platform/system.rs`; platform-specific APIs stay under `platform/macos/` and `platform/windows/`. Blocking system calls use Tokio's blocking pool where needed. macOS integrates CoreAudio, Quartz and Apple Events. Windows uses WASAPI, GSMTC, WinRT, `SendInput` and Win32 shell/window APIs. Some features have deliberate OS limits, listed in the [platform matrix](../apps/desktop/PLATFORM_STATUS.md) and [Windows test plan](../apps/desktop/docs/WINDOWS_TEST_PLAN.md). Linux distribution is deferred.

Native extensions are approved packages with a bounded JSON Lines protocol. The [extension SDK](../apps/desktop/extension-sdk/README.md) describes the manifest and lifecycle. They run with the current user's permissions.

Each extension owns its worker task and bounded command queue. Polls publish
cached snapshots, and native action handling releases the global action permit
before awaiting a worker. The extension catalog has its own revision so changes
can refresh editor choices without replacing unsaved page edits. See the
[SDK lifecycle](../apps/desktop/extension-sdk/README.md#protocol-and-lifecycle).

## Builds and updates

The [quality workflow](../.github/workflows/quality.yml) checks the shared editor, native backend, documentation and console. A version tag starts the [release candidate workflow](../.github/workflows/release.yml): it builds signed desktop packages and console packages into a draft GitHub Release. A separate, manually dispatched [publish workflow](../.github/workflows/publish-release.yml) makes that draft public after asset checks; repository owners should configure required reviewers on its `production` environment. With an embedded public key, the editor checks GitHub's `latest.json` after opening or on request in Settings. Installation is user-triggered, verifies the update signature and restarts the app. A release build needs the updater public key at compile time. See [Release process](RELEASE.md) for setup and remaining validation.

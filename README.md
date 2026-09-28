<div align="center">

<img src="docs/assets/3decks-banner.svg" alt="3Decks and Decky" width="100%">

# 3Decks

**Your Nintendo 3DS. Your desktop controls.**

[Installation](docs/INSTALLATION.md) · [Documentation](docs/README.md) · [Français](README.fr.md)

</div>

3Decks turns a homebrew-enabled 3DS or 2DS into a control surface for your computer. The desktop application is built with **Tauri 2, Rust and a shared React/HeroUI editor**. It discovers consoles on the local network, pairs each one, and serves live controls and dashboards.

## What is here

| Directory | Purpose |
|---|---|
| [`desktop/`](desktop/README.md) | Tauri desktop application for macOS and Windows, native integrations, tray and updater |
| [`frontend/`](frontend/README.md) | The React editor used by the desktop webview |
| [`3ds-app/`](3ds-app/) | Native C application for Nintendo 3DS and 2DS |
| [`docs/`](docs/README.md) | Current installation, architecture, protocol and release guides |

The macOS path has been exercised with Citra and Apple Music. Windows has native adapters and an [explicit validation plan](desktop/docs/WINDOWS_TEST_PLAN.md), but its release build still needs real-device qualification. Linux remains a later target. No public desktop release has been published yet.

## Build from source

Install Rust, Node.js 24, pnpm 11 and the [Tauri 2 platform prerequisites](https://v2.tauri.app/start/prerequisites/). From the repository root:

```sh
cd frontend && pnpm install --frozen-lockfile
cd ../desktop && npm ci && npm run tauri -- dev
```

Build the console with `./build.sh all` (Docker and devkitPro packaging image) or see the [console guide](docs/CONSOLE_PACKAGING.md). Only one desktop server can use UDP 38122 and TCP 38123 at a time.

## Security and releases

Console traffic uses a trusted local network; do not forward ports 38122 or 38123 to the internet. Native extensions execute with the user's permissions and require explicit approval. The [release workflow](docs/RELEASE.md) creates a **draft** after a version tag and validates signed updater assets before a maintainer publishes it. Apple and Windows distribution signing and real Windows tests are still release gates.

[GPL-3.0-only](LICENSE). Inter uses the [SIL Open Font License](docs/licences/Inter-OFL.txt). 3Decks is an independent homebrew project, not affiliated with Nintendo.

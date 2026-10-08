## 3Decks desktop and console

This draft contains native macOS and Windows desktop installers plus Nintendo 3DS homebrew packages. Download the installer for your OS and either `deck3ds.3dsx` or `deck3ds.cia` for the console. The desktop application bundles its Rust backend and React editor; Python is not required.

macOS packages are ad-hoc signed and not notarized. Windows installers are not Authenticode signed. See the [installation guide](https://github.com/RomualdYT/3Decks/blob/main/docs/INSTALLATION.md) for first-launch instructions.

Before publishing, verify Tauri updater signatures, `latest.json`, `SHA256SUMS.txt`, platform tests and the [release checklist](https://github.com/RomualdYT/3Decks/blob/main/docs/RELEASE.md). Windows notification history requires a packaged identity that the direct installer does not currently provide.

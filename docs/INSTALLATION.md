# Installation

Public desktop installers have not been published yet. Development builds are unsigned and intended for testing only. When a reviewed release is available, download the macOS DMG or Windows installer and `deck3ds.3dsx`/`.cia` from the same [GitHub Release](https://github.com/RomualdYT/3Decks/releases). Compare the download with `SHA256SUMS.txt` if desired.

1. Install the desktop application. On macOS, move 3Decks to Applications. On Windows, run the installer.
2. Install `deck3ds.3dsx` in `sdmc:/3ds/deck3ds.3dsx` for Homebrew Launcher, or install the `.cia` with FBI on custom firmware.
3. Put computer and console on the same trusted Wi-Fi network. Start the desktop app and follow the setup assistant.
4. Select the computer on the console and enter the six-digit pairing code shown by the app.

3Decks listens on UDP 38122 and TCP 38123 by default. If automatic discovery fails, use the console's manual IP/port option and check the computer firewall. Some macOS features prompt for Accessibility, Automation or Full Disk Access. Windows notification history requires a packaged identity and explicit user consent; the current direct installer has no such identity.

For a source build, see [Contributing](CONTRIBUTING.md). For console packaging details, see [Console packages](CONSOLE_PACKAGING.md).

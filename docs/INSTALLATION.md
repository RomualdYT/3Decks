# Install and pair

[Documentation](README.md) · [Français](INSTALLATION.fr.md)

## Requirements

- A Nintendo 3DS/2DS already able to run homebrew.
- A macOS or Windows computer; see [platform limitations](../apps/desktop/PLATFORM_STATUS.md).
- Both devices on the same trusted local network. The computer may use Ethernet.

## Install

Download the matching desktop and console packages from
[GitHub Releases](https://github.com/RomualdYT/3Decks/releases) when available.
For a source build, follow [Contributing](CONTRIBUTING.md). Release downloads
include `SHA256SUMS.txt` for checking file integrity.

1. **macOS:** open the DMG and move 3Decks into Applications. **Windows:** run the installer.
2. **Homebrew Launcher:** copy `deck3ds.3dsx` to `sdmc:/3ds/deck3ds.3dsx`.
   **HOME Menu:** install `deck3ds.cia` with FBI on a custom-firmware console.
   See [console packages](CONSOLE_PACKAGING.md) for details.
3. Open 3Decks on the computer and follow the setup assistant. Enable the features you need.
4. Open 3Decks on the console, select the discovered computer and enter its six-digit pairing code.

Each console receives its own saved credential. Future connections do not need
another code unless access is revoked or the saved credential is lost.
Closing the desktop editor keeps the connection active; use **Quit** in the
system menu to stop the desktop app.

## Connection and permissions

Default ports are **UDP 38122** for discovery and **TCP 38123** for controls.
Allow the desktop app through the local-network firewall. If discovery fails,
enter the computer's numeric IPv4 address and TCP port in the console settings.

macOS may request Accessibility, Automation or Full Disk Access for selected
features. Grant only the access you intend to use. Windows notification history
is unavailable in the direct installer because it lacks a compatible package identity.

The desktop uses your saved language choice, otherwise French for a French
system/browser and English for other languages. The console starts in English;
its language is selectable in console settings.

Next: [create and configure pages](USAGE.md) or [troubleshoot a connection](TROUBLESHOOTING.md).

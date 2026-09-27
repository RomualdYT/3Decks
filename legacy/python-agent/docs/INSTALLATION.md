# Install 3Decks

[Documentation](README.md) · [Français](INSTALLATION.fr.md)

## Before you start

You need a homebrew-enabled Nintendo 3DS/2DS family console, macOS or Windows, internet access for installation, and a trusted local network shared by the computer and console. This project does not install homebrew on the console.

Use the files in a [GitHub Release](https://github.com/RomualdYT/3Decks/releases). The commands below require a release containing the named assets. If none is published, use [source setup](CONTRIBUTING_AGENT.md); do not assume the download links already work.

The launchers install a private Python runtime with uv and the versioned 3Decks wheel. You do not need Git, Node.js, a preinstalled Python or administrator installation. Read the downloaded script before running it if you want to inspect its operations.

## 1. Install on the computer

### macOS

Paste into Terminal:

```sh
installer="$(mktemp)" && curl -fL https://github.com/RomualdYT/3Decks/releases/latest/download/install-3decks-macos.sh -o "$installer" && sh "$installer"
```

Open **3Decks.app** from your user Applications folder on subsequent launches. An icon stays in the menu bar; the editor opens in your browser. This is a launcher-based installation, not a notarized standalone macOS binary. OS permissions remain under your control.

### Windows

Paste into PowerShell:

```powershell
$installer="$env:TEMP\install-3decks.ps1"; Invoke-WebRequest https://github.com/RomualdYT/3Decks/releases/latest/download/install-3decks-windows.ps1 -OutFile $installer; powershell -ExecutionPolicy Bypass -File $installer
```

Start menu and Desktop shortcuts are created. The menu icon appears near the clock, possibly behind the **^** overflow button. The execution-policy argument applies to this installer process; it is not an instruction to disable OS security globally.

**Windows notifications are unavailable in the direct GitHub install.** Reading them requires MSIX identity, the notification capability and explicit permission. Store packaging exists as a maintainer workflow; a published Store version is not assumed. No private Windows notification-database fallback exists. Other features still depend on native capabilities; see [platform limits](TROUBLESHOOTING.md).

## 2. Install on the console

**HOME menu:** on a console with custom firmware, install the release's
`deck3ds.cia` using FBI. Decky appears as the application icon, with a banner on
the upper screen. Follow the [HOME installation steps](CONSOLE_PACKAGING.md).

**Homebrew Launcher:** download `deck3ds.3dsx` from the same release and copy it to:

```text
sdmc:/3ds/deck3ds.3dsx
```

Open it from Homebrew Launcher. Choose a language, select the discovered computer by name and enter the short code shown in the computer editor's connection panel when prompted. The console saves its credential automatically.

If discovery fails, open **Manual setup** and enter the numeric IPv4 address (for example, `192.168.1.10`) and TCP port shown by the agent. This does not use the browser's `127.0.0.1` address. [Connection troubleshooting](TROUBLESHOOTING.md) explains the network checks.

## 3. Create your controls

Follow the [user guide](USAGE.md). The system menu reopens the editor after you close its browser tab. Closing the tab does not stop the agent; **Quit** in the system menu does.

## Update and uninstall

Run the same installation command to update. The launcher requests graceful shutdown before replacing the installed program. If an older instance cannot respond, quit it from its menu and retry; a shutdown timeout aborts the update rather than forcibly killing it.

Configuration, paired consoles and extension data are retained. Back them up before updating; see [storage locations](CONFIGURATION.md). On the console, install the newer CIA over the existing title, or replace the SD card's `.3dsx`, depending on the format you use.

To uninstall, download the installer as above and run the downloaded file with:

```sh
# macOS — use the path of the installer you downloaded
sh /path/to/install-3decks-macos.sh --uninstall
```

```powershell
# Windows — use the path of the installer you downloaded
powershell -ExecutionPolicy Bypass -File C:\Downloads\install-3decks-windows.ps1 -Uninstall
```

Uninstall removes application shortcuts and login startup, not user configuration or extension data. The shared uv tool itself may remain.

## What is verified

The generated launcher checks the exact release wheel's SHA-256 before installation. This detects a mismatch with its expected artifact; **it is not a code-signing certificate**, nor independent protection if the release account or installer itself is compromised. uv manages an isolated tool environment. Source/CI environments additionally use the repository lockfile.

For manual Python installation or an existing checkout, use [manual Python setup](PYTHON_SETUP.md). Maintainers should follow the separate [release procedure](PUBLIC_RELEASE.md).

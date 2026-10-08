# Desktop platform support

This matrix describes implemented adapters and distribution limits. A successful
build does not establish correct behaviour on every OS, device or player.
Release qualification should record the actual tested versions and hardware.

| Feature | macOS | Windows | Linux |
| --- | --- | --- | --- |
| Editor, settings, pairing, TCP/UDP, OBS, telemetry, extension host | Shared implementation | Shared implementation | Shared implementation; desktop distribution deferred |
| System volume and microphone | CoreAudio | WASAPI/COM | Not implemented |
| Media commands, metadata and position | Spotify/Apple Music through native adapters | Active GSMTC session; fields and commands depend on the player | Not implemented |
| Player volume | Spotify/Apple Music where exposed | WASAPI sessions matching the active media player | Not implemented |
| Artwork | Native media provider and shared Rust conversion | GSMTC thumbnail and shared Rust conversion | No native media provider |
| Online lyrics | Optional LRCLIB lookup from media metadata | Same shared lookup from GSMTC metadata | No native media provider |
| Audio outputs | List and direct selection through CoreAudio | List/default output; change it through Windows Sound settings | Not implemented |
| Launch/quit apps, paths and URLs | NSWorkspace/NSRunningApplication | Installed apps via Get-StartApps; ShellExecuteW by name/AppID, path or protocol; graceful WM_CLOSE for running apps | Not implemented |
| Keyboard shortcuts and lock | Quartz and system shortcut | SendInput and LockWorkStation | Not implemented |
| Windows and focus | CoreGraphics and Accessibility | EnumWindows and SetForegroundWindow | Not implemented |
| Other apps' notifications | Read-only usernoted SQLite access; Full Disk Access may be needed | UserNotificationListener requires compatible package identity and consent; unavailable in the direct installer | Not implemented |
| Release packages | Apple Silicon and Intel | x64 | No release target configured |

## Important limits

- Windows may block synthetic input to elevated applications (UIPI), or refuse
  foreground-window activation. These restrictions are reported as action errors.
- Windows audio-output selection opens Sound settings instead of forcing an
  undocumented global-output API.
- Direct Windows MSI/NSIS installers do not provide the package identity needed
  for notification history. For a compatible identity, observed notifications
  are cached locally for up to six hours and eight entries; disabling the
  feature or revoking access clears the cache.
- macOS notification reading depends on a private OS database format, which can
  change between system versions.
- Missing media metadata, GPU or temperature readings are unavailable values,
  not zero measurements.

The [Windows checks](docs/WINDOWS_TEST_PLAN.md) and
[release qualification guide](../../docs/QUALIFICATION.md) cover runtime validation.
Focus's Linux extension package is a standalone native binary; it does not imply
that the Linux desktop app has complete system integrations.

## Windows runtime validation — 7 October 2026

A native MSVC Tauri release build and an NSIS installer were produced on Windows
11 Pro x64 (build 26200, WebView2 154). Before integrating the subsequent main
changes, 32 Rust tests (including the Windows SDK worker) and 29 frontend tests
passed. The four native WebView2 views and successive saves were exercised.
Discovery, pairing, invalid-message rejection, token reconnection and revocation
were tested; a New Nintendo 3DS XL remained connected with the window closed.
Spotify metadata/artwork, audio-output enumeration and system-volume access
were observed. Chrome, Microsoft Store Calculator and Notepad launched correctly.

Windows app discovery found 185 entries on this PC. Targets remain editable,
and the file picker also supports executables and shortcuts absent from Start.
Discovery uses PowerShell without a profile, an eight-second timeout and a
60-second cache; manual targets remain usable when discovery is blocked.
Action failures are now written to the persistent diagnostic journal.

In the measured release session, aggregate private memory was approximately
303 MB with the editor and WebView2 open. Closing the window stopped WebView2:
approximately 20 MB private memory (58 MB working set) and 2.3% of one CPU core
were measured over 20 seconds with the real console connected. These snapshots
do not establish the 35 MB target for the entire application.

Windows 10, a fresh-profile installation, signing/updater validation, physical
multi-monitor DPI, sleep/resume, USB/Bluetooth devices, input to elevated apps
and volume control for an actively playing application remain to be qualified.

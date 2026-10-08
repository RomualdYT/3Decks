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
| Launch/quit apps, paths and URLs | NSWorkspace/NSRunningApplication | ShellExecuteW and graceful WM_CLOSE request | Not implemented |
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

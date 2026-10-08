# Windows runtime checks

Maintainer checklist for Windows 10/11. Record OS version, architecture, installer
type, WebView2 version, keyboard layout, DPI, audio devices and firewall state.
For each failure, keep reproduction steps, the displayed error and a sanitized log.
The release workflow targets x64; ARM64 requires its own build and qualification.

## Installation and lifecycle

1. Follow the [desktop build guide](../README.md#development) on Windows and build
   the NSIS/MSI installer. Check its signature and actual package identity.
2. Install on a fresh standard-user profile; check launch, tray, Start shortcut,
   uninstall and behaviour with missing/outdated WebView2.
3. Complete setup, restarting after each step to check saved progress and permissions.
4. Check the editor at 100/125/150/200% DPI and on multiple monitors.
5. Close/reopen the window, quit, enable login startup, restart and sleep/wake.
   The server should remain active when only the editor is closed.

## Network

- Allow/refuse firewall access, including UDP 38122 and TCP 38123.
- Wi-Fi, Ethernet, VPN, multiple adapters, network changes and reconnects.
- First pairing, saved-credential reconnect, revocation and re-pairing.
- Configuration saves, page changes, primary/hold actions and explicit errors.
- OBS with correct/incorrect credentials and an unavailable server.

## Native integrations

| Area | Checks and expected limits |
| --- | --- |
| System audio/micro | Volume endpoints, mute/unmute and USB/Bluetooth changes; controls target the default multimedia devices. |
| Audio outputs | List/default output refresh; the change control opens Windows Sound settings rather than forcing an endpoint. |
| Player volume | Several GSMTC players and multiple WASAPI sessions; unrelated apps' volumes must stay unchanged. |
| Media | Metadata, play/pause, next/previous, position, seeking, missing/large artwork and competing active sessions. Fields depend on the player. |
| Lyrics | Opt-in lookup, accents, ambiguous/missing tracks, offline behaviour and rapid track changes. |
| Shortcuts | Letters, digits, navigation/editing keys, Print Screen, F1–F12 and Ctrl/Alt/Shift/Win on AZERTY/QWERTY. Check elevated targets; UIPI may block input. |
| Open/quit apps | Executables, names, paths/URLs with spaces and non-ASCII text, missing targets, unsaved documents and tray apps. WM_CLOSE is a graceful request, not forced termination. |
| Windows | Multiple/minimized windows, disappeared targets and elevated apps; foreground policy may refuse activation. |
| Lock | Local and RDP sessions without stopping the desktop app. |
| Notifications | Direct installers must report unavailable. With a compatible identity/capability, check consent, refusal/revocation, observed history, restart, expiry and disabling the source. |

A compatible notification package needs `userNotificationListener`. The local
cache keeps up to eight observed notifications for six hours; disabling the
feature or revoking permission clears it. It is not a complete deleted-notification history.

## Extensions and updates

- Import the Windows Focus package, approve it, and select its source/dashboard.
  Check controls, localization, persistence, disable/restart and unapproved binaries.
- Check extension failures/timeouts alongside working native controls and another extension.
- Upgrade configuration without losing user pages or secrets.
- Check a signed update against published assets, installation/restart and data retention.
- Measure memory/CPU with editor open/closed, no console and multiple consoles.
  Use the [performance guide](../../../docs/PERFORMANCE.md), without unmeasured targets.

A cross-compilation check does not replace this native installer/runtime session.
See [Release qualification](../../../docs/QUALIFICATION.md).

# 3Decks desktop menu

[Documentation](README.md) · [Français](DESKTOP_INTEGRATION.fr.md)

The graphical installation keeps 3Decks in the **macOS menu bar** or the
**Windows notification area**. The editor remains a local browser page; the
menu is a lightweight control point that works without keeping that page open.

## User experience

The icon represents the console’s two screens. Green `#66CB10` means a console
is connected, gray means no console or suspended controls, and orange means a
component requires attention. Menu copy follows the operating-system language
in French or English.

The menu provides agent/console status, the editor and connection assistant,
timed or indefinite pause, quick integration settings, launch at login,
diagnostics and logs, restart, update lookup and a complete Quit action.

Suspending controls does not disconnect the console: dashboards continue to
update, while touch/value commands receive a human-readable refusal. Quick
settings are persistent and automatically appear in a clean editor session.
Disabling media preserves individual player/artwork preferences. Launch at login
is off by default; enabling it creates a per-user LaunchAgent or Startup shortcut.
Closing a browser tab leaves the agent running; Quit stops it.

## Graceful launcher shutdown

`deck3ds --stop` asks the graphical instance for the selected configuration to
quit and waits up to 30 seconds for its lock to be released. Supply the same
`--config` as at startup when using a custom path. No instance is a successful
no-op; a timeout returns a nonzero exit code and aborts the installer update.
Control uses a private file and a fresh random instance identifier, not an HTTP
endpoint or forced PID termination. Older versions without this control must
be quit from their menu. Headless instances retain their normal Ctrl+C/service
shutdown procedure.

## Maintainer architecture

`agent/backend/deck3ds/desktop` is an isolated adapter layer:

| Module | Responsibility |
|---|---|
| `models.py` | immutable controller/menu contracts |
| `application.py` | lifecycle, thread-safe bridge and actions |
| `tray.py` | native menu construction and icon rendering only |
| `autostart.py` | macOS LaunchAgent and Windows Startup shortcut |
| `instance.py` | per-configuration lock and existing-instance handoff |
| `system.py` | browser, clipboard and log opening |
| `logging.py` | bounded persistent GUI log |
| `translations.py` | native French/English copy |

To add an item, extend `TrayActions`, implement it in `DesktopController`, then
render it in `PystrayTray`. A domain mutation must call a service; it must not
edit JSON, TCP clients or React state directly. The GUI receives only detached
`DesktopSnapshot` values, never the mutable runtime.

`pystray` requires the native loop on the macOS main thread. The runtime keeps
one `asyncio` loop in a non-daemon worker thread. Menu callbacks must therefore
remain non-blocking: `_submit()` crosses into async work and `_background()`
owns short synchronous OS actions with at most four admitted at once. Pause
countdown changes alone do not rebuild the native menu. GUI logging rotates
continuously, keeping at most 2 MiB active plus one backup.

## Native qualification

Before release, verify on both systems: icon state transitions, FR/EN copy, a
real 3DS connect/disconnect, timed pause, every persisted quick setting, second
launch, login startup, restart, log opening and shutdown without a residual
process. On Windows, also test from the Store MSIX because GitHub wheel installs
cannot provide notification package identity.

[Installation](INSTALLATION.md) · [Full architecture](ARCHITECTURE.md) ·
[Qualification](QUALIFICATION.md)

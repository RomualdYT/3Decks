# macOS tray and shortcut checks

Maintainer checklist for a built macOS application. Record macOS version,
architecture, keyboard layout, build mode and console/emulator used. Quit an old
instance before opening a newly installed bundle. Grant Accessibility to the
bundle being checked when requested.

## Keyboard shortcuts

- Letters and digits with Command, Control, Option and Shift on AZERTY/QWERTY.
- Escape, Enter, Tab, Space, Backspace and forward Delete.
- Arrows, Home/End, Page Up/Down and F1–F12.
- Function keys with the relevant macOS keyboard preference enabled/disabled.
- Supported aliases and an invalid key; no modifier should remain pressed after an error.

## System menu and lifecycle

- Status with zero, one and two connected consoles.
- Open the editor, connection view and status after closing the window.
- Pause controls for 15 minutes, one hour and indefinitely. Mutations must be
  rejected while state/network updates continue. Check resume and timed expiry.
- Feature toggles and persistence after restart.
- Login startup, copied address, log access, restart and quit.
- A restart leaves one TCP/UDP listener; window size/position are restored.
- macOS window controls and header dragging without blocking interactive controls.

## Extensions

Import/enable Focus, configure its grid source and top screen, then check timer
controls, pause/resume, saved progress after restart and English/French labels.
A slow or failed extension must not block other extension workers or native controls.

Broader release checks are in [Qualification](../../../docs/QUALIFICATION.md).

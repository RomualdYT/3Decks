# Troubleshooting

[Documentation](README.md) · [Français](TROUBLESHOOTING.fr.md)

## No computer found

1. Check that 3Decks is running on the computer.
2. Put the computer and console on the same trusted LAN. Guest Wi-Fi, access-point isolation and VPN routing can prevent discovery.
3. Allow local-network traffic for the actual agent/Python executable in the OS firewall.
4. Try Manual setup with the agent's LAN address and TCP port, normally **38123**.

Automatic discovery uses **UDP 38122**. If manual TCP works but discovery does not, focus on broadcast/firewall routing rather than reinstalling the application. `127.0.0.1:38124` is the local editor, not the address to enter on the 3DS. Do not disable the firewall globally or forward ports to the internet.

## Pairing or session expired

Open the connection panel in the editor to obtain a current pairing code. Codes expire and are single-use. Repeated failures are rate-limited; wait before retrying. If a console was revoked, pair it again.

For an expired **browser session**, reopen the editor from the menu. Do not replace the persistent console token to fix a browser link.

## No menu icon

On Windows, check the **^** overflow beside the clock. On macOS, look for the two-screen icon in the menu bar; a narrow/crowded bar may hide items. Closing the browser does not remove it.

The plain CLI `deck3ds --ui` runs a terminal agent; use `deck3ds-ui` for the native desktop menu. If startup fails, inspect the log via the menu when available, or run the CLI with `--verbose`.

## Music or notifications unavailable

Check the integration toggle and status/permission information first.

| Platform | Important limit |
|---|---|
| macOS music | Spotify/Music automation permissions apply to the executable running the agent; a Python update can require permission again |
| macOS notifications | The adapter reads Notification Center's database read-only; OS privacy restrictions can block it |
| Windows notifications | GitHub/ordinary Python installation lacks required MSIX identity; there is no SQLite fallback |
| Windows media | Metadata depends on the player exposing a compatible Windows media session |
| Per-player volume | Not every platform/provider implements it |
| Performance metrics | GPU/temperature may be unavailable; macOS CPU display is load-derived, not an exact Task Manager equivalent |

Use the editor's permission shortcut to open the relevant settings, grant access to the correct application and restart if necessary. A shortcut opens settings; it cannot grant permission itself. Do not grant broad access simply to silence an unrelated error.

## File picker, app launch or OBS fails

A selected file/folder must still exist on this computer. Use the native picker again after moving it. App identifiers differ between platforms.

For OBS, enable its WebSocket server and match host, port (normally 4455) and password in 3Decks. Test the connection before assigning a scene. OBS must be running.

## Cannot save, or update cannot stop the agent

A configuration conflict means another writer changed the document. Preserve your intended edits, reload and reconcile. Invalid JSON should be repaired from a backup, not replaced blindly.

Quit 3Decks from its system menu before retrying an update that timed out. `deck3ds --stop` addresses the graphical instance for the selected config, so supply the matching `--config` for custom setups. Older instances may require manual Quit.

## Report a reproducible issue

Use the repository's [issue tracker](https://github.com/RomualdYT/3Decks/issues). Include OS, release version, console model, installation method, steps, expected/actual behavior and a short redacted error excerpt. Say whether manual connection works.

Do **not** attach complete config, SD settings, pairing registries, UI URLs, tokens, OBS passwords or unreviewed logs. Permission screenshots can also reveal personal notifications and app names.

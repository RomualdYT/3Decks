# Troubleshooting

[Documentation](README.md) · [Français](TROUBLESHOOTING.fr.md)

| Problem | What to check |
| --- | --- |
| Computer not found | Same LAN, guest-network isolation, VPN and firewall. Try manual IPv4/TCP setup. Defaults: UDP 38122, TCP 38123. |
| Port already in use | Quit the other desktop instance or the process using that port, then reopen 3Decks. |
| Pairing fails | Use the current six-digit code shown by the computer. A successful pairing replaces it. Revoke/re-pair if a saved credential no longer works. |
| Could not save to SD card | Settings are written to `sdmc:/3ds/deck3ds/settings.cfg`. Check free space, the SD adapter lock, and that `3ds/deck3ds` is a directory. Diagnostic builds show the operation (`mkdir`, `open`, `write`, `fflush`, `fsync`, `close`, `rename`) and its error code: include both in your report. Setup stays open when saving fails. |
| Permission-dependent action unavailable | Review the feature in Settings or reopen setup under Advanced. macOS permission changes may require quitting and reopening the app. |
| Windows audio output cannot be changed remotely | The direct installer shows the output and opens Windows Sound settings; selection happens on the computer. |
| Windows notifications unavailable | The direct installer lacks the package identity required by the Windows notification listener. |
| Lyrics missing | Enable media and online lyrics, check the track/artist metadata and try a track with synchronized lyrics. Not every track has a result. |
| Extension screen missing | Enable the extension, select its dashboard in the page's Top screen chooser, and select its source separately for generated buttons. Check the extension's error message. |
| Update unavailable | The build needs an embedded updater public key and a published signed update. Local builds without a key cannot use the updater. |

For help, use [Discord](https://discord.gg/EmdnneHeus) or open a GitHub issue.
Include app version, OS, console model, steps to reproduce and the displayed
error. Remove private paths, credentials and personal content from logs/screenshots.

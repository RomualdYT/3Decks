# Security

3Decks pairs each console with a code and stores a per-console token in the desktop application's configuration directory. The UDP discovery and framed TCP protocol are intended for a trusted LAN and are not encrypted. Do not forward ports 38122 or 38123 to the internet. Limit access through the OS firewall if the network is shared.

Native extensions run as the current user after explicit approval. Review their publisher and contents before installation. The updater verifies artifacts using an embedded public key; the private signing key belongs only in secured release infrastructure. The [release guide](RELEASE.md) describes distribution signing and publication gates.

## Tracked upstream dependency

Tauri 2's Linux GTK 3/WebKit stack brings in `glib` 0.18, which is affected by [GHSA-wrw7-89jp-8q8g](https://github.com/advisories/GHSA-wrw7-89jp-8q8g). The fixed `glib` 0.20 cannot replace it independently because the GTK bindings in this dependency chain use the 0.18 API. This crate is not in the macOS or Windows target graphs. Linux packages are not part of the first public release; revisit this dependency and the advisory before enabling Linux distribution. Keep the Dependabot alert open until an upstream-compatible fix is available.

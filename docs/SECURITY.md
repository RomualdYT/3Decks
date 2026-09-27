# Security

3Decks pairs each console with a code and stores a per-console token in the desktop application's configuration directory. The UDP discovery and framed TCP protocol are intended for a trusted LAN and are not encrypted. Do not forward ports 38122 or 38123 to the internet. Limit access through the OS firewall if the network is shared.

Native extensions run as the current user after explicit approval. Review their publisher and contents before installation. The updater verifies artifacts using an embedded public key; the private signing key belongs only in secured release infrastructure. The [release guide](RELEASE.md) describes distribution signing and publication gates.

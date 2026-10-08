# Security and privacy

[Documentation](README.md) · [Français](SECURITY.fr.md)

## Local network

Console discovery and controls use UDP/TCP without encryption. Pairing issues
an individual credential; the desktop stores its SHA-256 digest, and the console
stores the credential on its SD card. Revoke a console from the desktop settings
if you no longer want it to connect.

Use a trusted LAN. Do not forward ports 38122 or 38123 to the internet. Pairing
codes and credentials can be observed by someone who can inspect network traffic.

## Local data and optional services

Configuration may contain file paths, OBS credentials and extension settings.
Do not upload personal configuration, `paired-consoles.json`, the console's
`settings.cfg`, or logs containing private information in a bug report.

Online lyrics are optional and disabled by default. Enabling them sends track
title, artist and available album/duration metadata to LRCLIB. The console does
not contact the lyrics service. Update checks contact GitHub when an updater key
is configured. See [lyrics](../apps/desktop/docs/LYRICS_AND_PAGE_TEMPLATES.md) and
[release signing](RELEASE.md).

Stream chat is optional. The desktop connects to Twitch over HTTPS/WebSocket TLS
and stores access/refresh tokens in the system credential store. Recent
messages and badge images are sent to paired consoles over the local protocol.
Official badge images load from Twitch’s CDN without OAuth credentials. Messages are
kept in memory, not saved to disk. See [stream chat](STREAM_CHAT.md).

## Extensions

Importing a package does not execute it. Enabling it requires approval of its
SHA-256 fingerprint; changing the package requires a new approval. Native
extensions run with your account's permissions, in a separate process without
a sandbox. Their declared permissions describe intended access, not enforced
restrictions. Enable only code you trust.

## Reporting

Report ordinary bugs through GitHub issues or [Discord](https://discord.gg/EmdnneHeus).
For a security issue, use the repository's private vulnerability reporting
option if available. Do not post credentials or exploitation details publicly.

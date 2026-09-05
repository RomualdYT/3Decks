# Security and privacy

[Documentation](README.md) · [Français](SECURITY.fr.md)

## Intended environment

3Decks is a local desktop application for a **trusted LAN**. TCP protocol 1 is not encrypted or authenticated per message. Pairing codes and console credentials cross that channel. Pairing and replay checks do not protect against a network attacker observing it. Never expose TCP 38123 or UDP 38122 to the internet.

## Console permissions

The console normally sends configured page/button identifiers, not executable commands. The agent resolves and validates actions locally. Built-in direct controls have a separate limited allow-list. Scripts must already be declared in the trusted local file.

Pairing creates an individually revocable console credential; only its SHA-256 digest is stored in the paired-device registry. Legacy shared tokens are exchanged during migration. Handshake deadlines, connection caps, monotonic mutation IDs and pairing rate limits bound common abuse, but are not encryption.

## Local editor

HTTP listens only on `127.0.0.1`. Its per-start session is distinct from console credentials. Host/Origin checks, request-size/time limits and browser security headers protect local operations. The authenticated config API contains sensitive settings: keep the session and its initial URL private.

The session is temporarily present in the initial link and private desktop handoff state. Do not publish browser/session storage, cache directories or logs without review. The browser removes the token from the visible URL after reading it.

## Extensions and native permissions

Extensions run as your OS user. Separate processes and declared permissions are **not a sandbox** and do not stop filesystem/network access. Approve only reviewed packages. A changed fingerprint requires approval again. Password-typed settings are redacted from catalogs, not magically encrypted everywhere.

OS permissions remain necessary. macOS notification collection uses a read-only native database provider. Windows uses the notification listener API only, with MSIX identity and user consent; no SQLite fallback.

## Reporting a concern

Do not post secrets or exploit details in a public issue. If GitHub private vulnerability reporting is enabled for the repository, use its Security tab. Otherwise contact the maintainer through an available private channel before sharing sensitive material. This document does not promise a private reporting channel that has not been enabled.

Before making a fork public, audit its files **and history**. The bundled public-config checker covers selected fields in one demonstration file only; it is not a comprehensive secret scanner. Rotate any exposed credential before considering history cleanup.

# Documentation

[Project home](../README.md) · [Français](README.fr.md)

Start with the guide matching your task. English documents are the reference; translations use the same filename with a `.fr.md` suffix. Protocol identifiers, commands and generated OpenAPI remain unchanged across languages.

## Use 3Decks

| Guide | What you will learn | French |
|---|---|---|
| [Installation](INSTALLATION.md) | Requirements, releases, pairing, updates and removal | [FR](INSTALLATION.fr.md) |
| [User guide](USAGE.md) | Pages, buttons, dashboards, console controls | [FR](USAGE.fr.md) |
| [Configuration](CONFIGURATION.md) | Storage, backups, scripts, concurrent edits | [FR](CONFIGURATION.fr.md) |
| [Desktop menu](DESKTOP_INTEGRATION.md) | Status, quick settings, pause, startup and quit | [FR](DESKTOP_INTEGRATION.fr.md) |
| [Troubleshooting](TROUBLESHOOTING.md) | Discovery, permissions, media, notifications | [FR](TROUBLESHOOTING.fr.md) |
| [Security](SECURITY.md) | Trusted LAN, credentials and extension trust | [FR](SECURITY.fr.md) |

## Build and extend

| Guide | Scope | French |
|---|---|---|
| [Contributing](CONTRIBUTING_AGENT.md) | Source setup, frontend proxy, tests and build | [FR](CONTRIBUTING_AGENT.fr.md) |
| [Extensions](EXTENSIONS.md) | API 1 SDK, manifests, stdio and console contributions | [FR guide](EXTENSIONS.fr.md) |
| [Architecture](ARCHITECTURE.md) | Layers, transactions, resource ownership | [FR overview](ARCHITECTURE.fr.md) |
| [HTTP API](api/README.md) | Local session, routes, errors, OpenAPI | [FR guide](api/README.fr.md) |
| [Console protocol](PROTOCOL.md) | UDP discovery, TCP framing, state and artwork | [FR](PROTOCOL.fr.md) |
| [Migration](MIGRATION_FASTAPI.md) | Python 3.12+, old configurations and rollback | [FR](MIGRATION_FASTAPI.fr.md) |

## Maintain and release

- [Release checklist](PUBLIC_RELEASE.md) ([FR](PUBLIC_RELEASE.fr.md)): build, GitHub and Store submission boundaries.
- [Qualification](QUALIFICATION.md) ([FR](QUALIFICATION.fr.md)): dated evidence and outstanding native checks.
- [Code quality](CODE_QUALITY.md) ([FR](CODE_QUALITY.fr.md)): automated gates and maintainability priorities.
- [Local application and performance](LOCAL_APP.md) ([FR](LOCAL_APP.fr.md)): design decisions and measured tradeoffs.

## Documentation policy

Update user instructions with the behavior they describe. Put platform limits next to the feature, not only in release notes. Keep English first and translations separate; label summaries as summaries instead of implying full translation parity. Never include real configuration, tokens or private logs in examples.

Keep test counts in the qualification report, dated and scoped. Keep benchmark data in `performance/`; do not silently replace historical results with current claims. Before proposing a change, run `python3 tools/check_docs.py` from the repository root to check local links.

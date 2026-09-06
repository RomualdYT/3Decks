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
| [Testing](TESTING.md) | Test responsibilities, isolation and checks | [FR](TESTING.fr.md) |
| [Contributing](CONTRIBUTING_AGENT.md) | Source setup, frontend proxy, tests and build | [FR](CONTRIBUTING_AGENT.fr.md) |
| [Extensions](EXTENSIONS.md) | API 1 SDK, manifests, stdio and console contributions | [FR guide](EXTENSIONS.fr.md) |
| [Architecture](ARCHITECTURE.md) | Layers, transactions, resource ownership | [FR overview](ARCHITECTURE.fr.md) |
| [HTTP API](api/README.md) | Local session, routes, errors, OpenAPI | [FR guide](api/README.fr.md) |
| [Console architecture](CONSOLE_ARCHITECTURE.md) | C modules, network budgets, text cache and host tests | [FR](CONSOLE_ARCHITECTURE.fr.md) |
| [Console packages](CONSOLE_PACKAGING.md) | HOME installation, CIA/3DSX builds, Decky icon and banner | [FR](CONSOLE_PACKAGING.fr.md) |
| [Console protocol](PROTOCOL.md) | UDP discovery, TCP framing, state and artwork | [FR](PROTOCOL.fr.md) |
| [Manual Python setup](PYTHON_SETUP.md) | Manual wheel installation and configuration selection | [FR](PYTHON_SETUP.fr.md) |

## Maintain and release

- [Release checklist](PUBLIC_RELEASE.md) ([FR](PUBLIC_RELEASE.fr.md)): build, GitHub and Store submission boundaries.
- [Qualification](QUALIFICATION.md) ([FR](QUALIFICATION.fr.md)): native release checklist and evidence to record.
- [Code quality](CODE_QUALITY.md) ([FR](CODE_QUALITY.fr.md)): automated gates and maintainability priorities.
- [Performance measurement](PERFORMANCE.md) ([FR](PERFORMANCE.fr.md)): repeatable current-agent scenarios.

## Documentation policy

Update user instructions with the behavior they describe. Put platform limits next to the feature, not only in release notes. Keep English first and translations separate; label summaries as summaries instead of implying full translation parity. Never include real configuration, tokens or private logs in examples.

Keep test outcomes in the release report, dated and scoped. Document reproducible performance scenarios instead of development-session comparisons. Before proposing a change, run `python3 tools/check_docs.py` from the repository root to check local links.

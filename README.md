<div align="center">

<img src="cover.png" alt="3Decks: a Nintendo 3DS controlling a computer" width="100%">

# 3Decks

**Your Nintendo 3DS. Your desktop controls.**

<p>
<img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-66CB10?style=flat-square" alt="macOS and Windows">
<img src="https://img.shields.io/badge/console-3DS%20%7C%202DS%20%7C%20New%203DS-66CB10?style=flat-square" alt="3DS, 2DS and New 3DS">
<img src="https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat-square" alt="Python 3.12 or newer">
<img src="https://img.shields.io/badge/license-GPL--3.0-F59E0B?style=flat-square" alt="GPL-3.0 license">
</p>

Build a personal control surface for macOS and Windows, with a visual editor on your computer and live dashboards on your console.

[Get started](docs/INSTALLATION.md) · [Documentation](docs/README.md) · [Create an extension](docs/EXTENSIONS.md) · [Français](README.fr.md)

</div>

## Two screens, one useful companion

- **Make it yours:** pages, icons, colors, shortcuts and drag-and-drop organization.
- **Control your computer:** apps, files, folders, windows, volume and audio outputs.
- **Stay in the flow:** Spotify, Apple Music on macOS, album artwork and OBS controls.
- **See what matters:** now playing, computer performance and supported desktop notifications.
- **Extend it:** community packages can add actions, generated pages and dashboards.
- **Keep it close:** a macOS menu-bar or Windows notification-area menu opens the editor, pauses controls and quits the agent.

The editor uses React, HeroUI and Inter. The console shows native controls and dashboards; integrations run on your computer, not on the 3DS.

## Get started

You need a homebrew-enabled **3DS, 2DS or New 3DS**, a **Mac or Windows PC**, and a trusted local network shared by both.

1. [Install the computer app](docs/INSTALLATION.md) using a GitHub Release launcher.
2. Copy the release's `deck3ds.3dsx` to `sdmc:/3ds/deck3ds.3dsx` and open it in Homebrew Launcher.
3. Select your computer by name and enter the pairing code shown in the editor.
4. [Create your first page](docs/USAGE.md), save it and try a button.

The launchers prepare Python for you. **No Git, Node.js or preinstalled Python is required for a release installation.** If no release assets are available yet, follow the [source setup](docs/CONTRIBUTING_AGENT.md).

### Know before installing

- Notifications depend on OS permissions. **The direct GitHub installation cannot read Windows notifications:** an MSIX identity and user approval are required. Store packaging is prepared; this README does not announce a published Store app.
- Some integrations expose different capabilities on macOS and Windows. The editor reports availability.
- Console traffic is **not encrypted**. Use a trusted LAN; never forward the agent's ports to the internet.
- Extensions execute with your account's permissions. Install only code you trust.

See [troubleshooting and platform limits](docs/TROUBLESHOOTING.md) and the [security model](docs/SECURITY.md).

## Documentation

| I want to… | Start here |
|---|---|
| Install, update or uninstall | [Installation](docs/INSTALLATION.md) |
| Pair my console and build controls | [User guide](docs/USAGE.md) |
| Understand settings, files and backups | [Configuration](docs/CONFIGURATION.md) |
| Use the menu next to the clock | [Desktop menu](docs/DESKTOP_INTEGRATION.md) |
| Fix a connection or permission problem | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Build my own integration | [Extension API 1](docs/EXTENSIONS.md) |
| Contribute or build from source | [Contributor guide](docs/CONTRIBUTING_AGENT.md) |
| Explore the implementation | [Architecture](docs/ARCHITECTURE.md), [HTTP API](docs/api/README.md), [3DS protocol](docs/PROTOCOL.md) |

[All documentation](docs/README.md) includes setup, testing and release procedures. English is the reference language; French guides are separate and linked from each available translation.

## Development

The backend requires Python **3.12+**. CI targets Python 3.12–3.14 on Linux, macOS and Windows; Linux tests the portable core, not native desktop integrations. Frontend builds use Node.js 24 and pnpm; console builds use devkitPro or Docker.

See the [complete setup and checks](docs/CONTRIBUTING_AGENT.md). Test results and native checks still to perform are recorded in [Qualification](docs/QUALIFICATION.md), not presented as blanket cross-platform certification.

## License

[GPL-3.0-only](LICENSE). Inter is distributed under the [SIL Open Font License](docs/licences/Inter-OFL.txt). Keep third-party license notices when distributing builds. This is an independent homebrew project, not affiliated with Nintendo.

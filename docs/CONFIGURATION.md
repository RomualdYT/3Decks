# Configuration and backups

[Documentation](README.md) · [Français](CONFIGURATION.fr.md)

Use the visual editor for normal configuration. Manual JSON editing is intended for advanced users and contributors.

## Where data lives

| Launch mode | Selected configuration |
|---|---|
| Explicit `--config PATH` | That path |
| Source checkout without `--config` | Historical `agent/config.json`, when present |
| Installed package | OS user configuration directory |

Typical installed locations are `~/Library/Application Support/3Decks/config.json` on macOS and `%LOCALAPPDATA%\3Decks\config.json` on Windows; platformdirs resolves the actual directory. The current working directory does not select an installed application's configuration.

Beside the selected file, the agent keeps `paired-consoles.json` and `extensions/`. Back up the **whole selected configuration directory**, including extension approvals, packages and data, with the agent stopped. Treat backups as private: config may contain OBS credentials, script commands and the legacy console token.

Console-side settings and its pairing credential stay on the SD card. Removing a paired console in the editor revokes its credential and closes matching connections.

## Safe source development

Never save personal settings into the tracked demonstration file. From `agent/`:

```sh
uv run --locked deck3ds --config config.local.json --init-config
uv run --locked deck3ds-ui --config config.local.json
```

The first command refuses to overwrite any existing file. `config.local.json` is ignored by Git but is **not selected automatically**: keep passing `--config`. The GUI entry creates a default configuration only if the selected file is absent, never if it is invalid.

## Document versus console view

The JSON document stores user choices: localized page titles, grid/list layout, dashboard/source selection, button appearance/actions, integration settings and scripts. Windows and extension-generated items belong to a separate resolved console view and are not persisted as user buttons.

Action short forms and bilingual labels remain supported. Instead of maintaining a second static action catalog here, use the editor or authenticated `GET /api/schema`: it reports the installed version's exact arguments, defaults, limits and platform capabilities.

## Saving and conflicts

Saves validate the complete document, preserve the trusted `scripts` section, check revision and disk fingerprint, write a same-directory temporary file and atomically replace the document. Memory changes only after a successful write. A disconnected console does not undo a saved configuration.

A concurrent save or detected external edit returns `409 config_conflict`. Reload, reconcile your changes and save again. An external editor does not participate in the agent's lock; avoid simultaneous file/UI editing. Invalid external JSON leaves the current valid configuration in memory.

## Scripts

The editor cannot modify the `scripts` section. An advanced user may declare a named program as an argument array in the local file, then assign a `script.run` action to that name. Only declare programs you trust; never publish personal command paths or credentials.

Validate an edited file with:

```sh
uv run --locked deck3ds --config config.local.json --check
```

## Sessions are not console credentials

The local editor's session changes on restart. Reopen the editor from the system menu if a saved browser link expires. This is separate from the console's durable credential. A private desktop handoff file may contain the current UI link; do not share runtime/cache files.

For upgrades and rollback, see [migration](MIGRATION_FASTAPI.md). For the HTTP contract, see [API reference](api/README.md).

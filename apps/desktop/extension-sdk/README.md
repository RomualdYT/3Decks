# Native extension SDK · API 1

[User guide](../../../docs/EXTENSIONS.md) · [Complete Focus example](../../../examples/extensions/focus/README.md)

A 3Decks extension is a native executable distributed in a `.3deckext` ZIP.
The host launches the approved binary in a separate process and exchanges JSON
Lines over stdin/stdout. It runs with the user's permissions, without a sandbox.
Declared permissions describe intended access rather than enforcing restrictions.

## Rust API

The `three-decks-extension-sdk` crate provides `Context`, `Snapshot`,
`ActionResult`, the `Extension` trait and `serve()`:

- `initialize`: read settings and load saved data from `Context.data_dir`.
- `poll`: return current states, button sources and dashboards.
- `action`: handle a declared action and return success or failure.
- `shutdown`: optional protocol handler. Save important changes as they happen;
  host shutdown/disable can terminate the worker without calling this handler.

Use a Git or path dependency during development. Rust edition 2024 is used by
the SDK; the wire protocol remains language-independent.

From the repository root:

```sh
cargo build --release --locked --manifest-path apps/desktop/extension-sdk/Cargo.toml --example counter
python3 examples/extensions/focus/package.py
```

[Counter](examples/counter.rs) is a minimal implementation.
[Focus](../../../examples/extensions/focus/README.md) demonstrates typed settings,
dynamic buttons, dashboards and atomic persistence.

## Package and manifest

Place `extension.json` at the archive root and compiled binaries under `bin/`.
This manifest matches the Counter example, including its declared dashboard:

```json
{
  "api_version": 1,
  "id": "com.example.counter",
  "version": "1.0.0",
  "name": {"en": "Counter", "fr": "Compteur"},
  "description": {"en": "Counts button presses", "fr": "Compte les appuis"},
  "author": "Example",
  "runtime": "native",
  "binaries": {"darwin-aarch64": "bin/counter"},
  "permissions": [],
  "poll_interval": 2,
  "actions": [{"id": "increment", "title": {"en": "Increment", "fr": "Incrémenter"}, "arguments": []}],
  "sources": [],
  "dashboards": [{"id": "overview", "title": {"en": "Counter", "fr": "Compteur"}}],
  "settings": []
}
```

Change the binary mapping to match the files actually included. Supported keys:
`darwin-aarch64`, `darwin-x86_64`, `win32-aarch64`, `win32-x86_64`,
`linux-aarch64`, `linux-x86_64`. These are package target IDs, not interface labels.
Windows binaries use `.exe`. The host derives `platforms` from these mappings.
It runs the binary from the extracted package and sets its executable permission
on macOS/Linux. Script/command runtimes and external executable paths are rejected.

Limits: 4 MiB compressed, 16 MiB extracted, 256 ZIP entries; no symlinks or unsafe
paths. A manifest supports up to 32 actions, eight sources, eight dashboards and
16 settings. Poll intervals range from 0.5 to 60 seconds.

Settings and action arguments use `name`, `type`, optional `default`, `required`,
`label` and `description`. Supported types: `text`, `password`, `number`,
`boolean`, `select`. Numbers can have `min`/`max`; select choices contain `value`
and a localized `label`. Password defaults are forbidden. Labels and descriptions
can be plain strings or objects such as `{"en":"Start","fr":"Démarrer"}`.

## Contribution data

`Snapshot.states` contains up to 32 boolean values. For individually configured
extension buttons, a state with the action's ID controls its active appearance.

Each declared source returns an ordered array of up to 32 items:

```json
{
  "id": "start",
  "label": {"en": "Start", "fr": "Démarrer"},
  "detail": {"en": "Begin a session", "fr": "Lancer une session"},
  "icon": "play",
  "color": "#66CB10",
  "active": false,
  "action": {"id": "start", "arguments": {}}
}
```

The referenced action must be declared in the manifest and its arguments must
match the declaration. Item IDs must be unique. Labels are limited to 64 UTF-8
bytes and details to 80; the console further limits displayed text. Use the
[console icon names](../../../docs/PROTOCOL.md#configuration-snapshot) for consistent rendering.
A grid uses the first six items; a list can display all 32.

Each declared dashboard returns a title and up to four cards:

```json
{
  "title": {"en": "Focus", "fr": "Focus"},
  "status": "ok",
  "cards": [{
    "label": {"en": "Remaining", "fr": "Temps restant"},
    "value": "24:12",
    "detail": {"en": "Session running", "fr": "Session en cours"},
    "progress": 4
  }]
}
```

Status can be `neutral`, `ok`, `warning` or `error`; progress is optional, 0–100.
Worker limits are 64 UTF-8 bytes for the title, 48 for a card label, 40 for its
string value and 80 for detail. The host resolves localized text for each console.
Cards are declarative; there is no custom HTML, drawing API or code download to the 3DS.

## Protocol and lifecycle

Requests and responses are one JSON object per line; responses echo the request
ID. Stdout is reserved for protocol data; write diagnostics to stderr.

| Method | Parameters | Result |
| --- | --- | --- |
| `initialize` | `api_version`, `extension_id`, `settings`, `data_dir`, `platform` | `{"api_version":1}` |
| `poll` | `{}` | `states`, `sources`, `dashboards` |
| `action` | `action`, `arguments` | `ok`, `message` |
| `shutdown` | `{}` | `{}` |

Each line is limited to 64 KiB and each exchange to five seconds. The host keeps
a separate serialized queue per worker, with up to 16 pending commands. A full
queue rejects new commands; slow workers do not hold the other extensions' queues.
Activation remains `starting` until initialization succeeds.

Use `ActionResult::failure` for an expected rejected operation. Protocol errors,
handler errors and timeouts stop the worker and put the extension in error.
Disable terminates the process and cancels pending calls. Changing settings
restarts the worker, so keep persistent state in `data_dir` and validate it on load.
Do not rely on receiving a graceful shutdown to save user progress.

The host validates contributions against the manifest. Sensitive settings are
masked in the interface but delivered to the process. Updating package contents
changes its fingerprint and requires renewed approval. Keep contribution IDs
stable across updates to preserve configured pages and shortcuts.

The SDK is licensed under [GPL-3.0-or-later](../../../LICENSE).

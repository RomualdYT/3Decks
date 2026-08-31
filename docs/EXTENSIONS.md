# 3Decks extensions — API 1

An extension adds actions, generated button pages and top-screen dashboards
without modifying the agent, React frontend or 3DS application. A package runs
on the **computer**, not on the console. macOS, Windows and Linux use the same
extension protocol. Platform-specific integrations must declare their supported
operating systems and implement the relevant OS APIs themselves.

## Pour commencer (FR)

Dans **Extensions**, importez un paquet `.3deckext` ou `.zip`, lisez sa
description et son auteur, configurez ses champs puis choisissez **Vérifier et
activer**. L'importation seule n'exécute rien. Les actions apparaissent dans
**Éditeur → Ajouter une action → Extensions** ; les contenus automatiques et
écrans se choisissent dans les réglages de chaque page. Ils fonctionnent en
grille 3 × 2 ou en liste. En cas d'erreur, les autres intégrations continuent.

Une extension activée possède les droits de votre compte utilisateur. Les
« accès » affichés sont des déclarations, **pas une sandbox**. Ne partagez pas
vos secrets dans le manifeste ou les paramètres d'un bouton : utilisez les
réglages de type `password`. Le guide ci-dessous est le contrat de référence.

## 1. Create your first extension

Requires Python 3.9+ (the same interpreter used to start the source-based agent).
No SDK installation or additional dependency is needed. From the repository's
`agent` directory, on macOS/Linux or Windows PowerShell:

```sh
python -m deck3ds.extensions init ../my-counter --id com.example.counter
python -m deck3ds.extensions validate ../my-counter
python -m deck3ds.extensions pack ../my-counter -o counter.3deckext
```

Use `python3` instead of `python` where appropriate. These commands **never
execute extension code**. They refuse to overwrite an existing directory or
archive. `validate` checks the manifest, files and fingerprint; it does not test
the behavior of handlers.

Import `counter.3deckext` from the UI. Review and enable it. Create a page,
choose **My counter** for the top screen, add **Increment** as an action, and
save. A tap increments the value on the console. The generated code persists
the counter through restarts.

A richer, dependency-free example is provided at
[`examples/extensions/focus-timer`](../examples/extensions/focus-timer): timer,
typed settings, action parameters, stateful buttons, generated grid/list and
four dashboard cards. Package it with:

```sh
python -m deck3ds.extensions pack ../examples/extensions/focus-timer -o focus.3deckext
```

## 2. Architecture and boundaries

```text
Installed package (extension.json + program + assets)
        │ explicit approval of the package SHA-256
        ▼
Agent extension manager ── JSON lines / stdio ── extension subprocess
        │ validated and cached contributions
        ├── React: generated settings, action catalogue, live previews
        └── existing authenticated TCP protocol
                       └── 3DS: native cards, grid/list, action feedback
```

The host modules are split by responsibility under
`agent/backend/deck3ds/extensions/`: `manifest`, `packages`, `worker`, `manager`,
`output`, `bridge`, `sdk`, and `scaffold`. Only `sdk` and the documented JSON
protocol are public APIs; do not import other host internals in an extension.

The 3DS uses `extension_ui.c/.h` for bounded parsing and native card rendering.
Existing command acknowledgements provide pending/success/error feedback.
Active-state overlays apply to grid buttons; list entries use their `active`
flag. No extension scripts, arbitrary markup or downloaded executable code are
sent to the console. There is no custom HTML/JS injection into the frontend.

Built-in Spotify, Apple Music, OBS, notifications and other integrations remain
built in. This API is an additive boundary; it does not pretend those existing
implementations have all been migrated to packages.

## 3. Package and manifest

```text
my-extension/
  extension.json           required, at the archive root
  main.py                  Python entrypoint (or command runtime program)
  README.md                installation, permissions, configuration, support
  LICENSE                  your chosen distribution license
  vendor/                  optional distributable dependencies
```

`.3deckext` is a ZIP with no extra enclosing directory. Maximum 4 MiB compressed,
16 MiB extracted and 256 entries. No symlinks, traversal paths, absolute paths,
encrypted entries or case-insensitive duplicate filenames. Up to 64 packages
can be installed. All packaged files are included in the fingerprint, including
bytecode caches; remove unnecessary generated files before packaging. Windows
device names and non-portable paths are refused on every OS. Packages should be
immutable while enabled; put mutable
data in the provided data directory.

[`extensions/manifest.schema.json`](extensions/manifest.schema.json) provides
IDE completion and structural validation. The Python validator is authoritative
for bounds, file existence, unique IDs and cross-field validation.

Minimal manifest (the CLI generates a complete runnable implementation):

```json
{
  "api_version": 1,
  "id": "com.example.counter",
  "version": "1.0.0",
  "name": {"en": "My counter", "fr": "Mon compteur"},
  "description": "A counter controlled from your console.",
  "author": "Your name",
  "runtime": "python",
  "entrypoint": "main.py",
  "platforms": ["darwin", "win32", "linux"],
  "permissions": ["filesystem"],
  "poll_interval": 1,
  "settings": [],
  "actions": [{"id": "increment", "title": "Increment", "icon": "plus"}],
  "sources": [],
  "dashboards": [{"id": "counter", "title": "Counter"}]
}
```

| Property | Contract |
| --- | --- |
| `api_version` | Integer `1`. Unsupported major APIs are refused. |
| `id` | 3–48 lowercase characters, starts with a letter, then letters/digits/dot/hyphen. Reverse-domain recommended; keep stable across upgrades. |
| `version` | `major.minor.patch`, optional `-prerelease`; no automatic update checks. |
| `name`, `description` | String or `{ "en": "…", "fr": "…" }`. English required; French falls back to English. Name ≤64 chars, description ≤300. |
| `author` | Required display string ≤100 chars. Self-declared, not a verified identity. |
| `platforms` | `darwin`, `win32`, `linux`; defaults to all three. |
| `permissions` | Informational declarations: `network`, `filesystem`, `system`, `notifications`. They do not grant or restrict OS rights. |
| `runtime` | `python` (default) or `command`. |
| `entrypoint` | Relative existing Python file, default `main.py`. |
| `command` | For command runtime: nonempty argv array, max16 elements, ≤512 chars each. No shell expansion or shell interpolation. |
| `poll_interval` | 0.5–60 seconds, default2. Scheduling is best-effort; slow extensions may reduce refresh frequency. |
| `settings` | ≤16 typed fields configured from Extensions. |
| `actions` | ≤32 declared actions. |
| `sources`, `dashboards` | ≤8 contributions of each kind. |

Contribution IDs: 1–32 characters, lowercase letter first, then lowercase
letters/digits/underscore/hyphen. Unique **within their group**. Each contribution
has `id`, localized `title` (≤64), optional localized `description` (≤300),
`icon` (built-in icon name, ≤16), and `color` (`#RRGGBB`, default `#66CB10`).
Use existing icon names from `/api/schema`; unknown names render the generic
icon. The frontend does not load arbitrary SVG from a package.

Actions may have `arguments` (typed fields) and `state` (a key from `poll.states`).
Their qualified reference is `ext:com.example.counter/increment`. Sources and
dashboards use the same qualified syntax in their respective page fields.
IDs are not translated. Avoid changing published IDs; configuration files retain
references to missing packages so shared layouts remain portable.

### Typed settings and action parameters

Each field has `name`, `type`, optional localized `label` and `description`,
`required` (default false), and optional `default`. Types:

| Type | UI / validation |
| --- | --- |
| `text` | Text field; string ≤2048 chars. |
| `password` | Masked field; stored settings are not returned to the UI. No manifest default allowed. |
| `number` | Number field; finite numeric value, optional `min`/`max`; booleans rejected. |
| `boolean` | Switch; JSON true/false only. |
| `select` | Select with 1–32 `choices`: `{ "value": "id", "label": "Name" }`. |

Field names follow the contribution-ID pattern. `type` is reserved for action
arguments. Unknown parameters are rejected. Defaults are applied before handlers
run. Missing optional values are omitted; do not assume a key exists without a
default. Empty optional strings remain empty strings. Required fields reject an
empty string. Save secrets as **settings**, not as per-button arguments: arguments
are part of shareable config files (even if their editor control is masked).

Settings are stored separately from the deck configuration. Applying settings
immediately restarts an enabled extension. Omitted password fields preserve
their existing value; an explicitly supplied empty string clears an optional
secret. Clearing a required secret is rejected. Settings are plaintext at rest
with restrictive POSIX file permissions (0600); Windows uses inherited ACLs.
There is no OS-keychain integration in API 1. Authors must not expose secrets
in dashboard values, source labels, logs or action messages.

## 4. Python SDK

```python
from deck3ds.extensions.sdk import Extension, Result, Snapshot

extension = Extension()

@extension.initialize
def initialize(context):
    # context.settings: validated settings with defaults
    # context.data_dir: private persistent storage directory (pathlib.Path)
    # context.platform: darwin / win32 / linux
    # context.extension_id: manifest id
    pass

@extension.action("increment")
def increment(context, arguments):
    data = context.load(default={"count": 0})
    data["count"] += 1
    context.save(data)
    return Result(ok=True, message=str(data["count"]))

@extension.poll
def poll(context):
    data = context.load(default={"count": 0})
    return Snapshot(dashboards={"counter": {
        "title": "Counter", "status": "ok",
        "cards": [{"label": "Count", "value": str(data["count"])}]
    }})

@extension.shutdown
def shutdown(context):
    pass  # best effort: persist important data earlier, not only here

if __name__ == "__main__":
    extension.serve()
```

Handlers are synchronous and serialized in a worker. Do not block indefinitely;
set timeouts on HTTP/OS calls (preferably <3s). Cache expensive work. `poll`
returns a **full replacement snapshot**, not a patch. Returning empty sources or
panels clears them. Action handlers return `Result`, an equivalent dictionary,
or `None` for empty success. A handler exception becomes a generic error; the SDK
writes its traceback to stderr, never to the console protocol.

`Context.load(name="state.json", default=None)` and `save(value, name="state.json")`
support simple JSON filenames only. Saves replace the file atomically. A damaged
JSON file raises an error; authors may catch it to offer a domain-specific repair.
The data directory is preserved when the package is removed or upgraded.

The host explicitly adds its backend SDK and package directory to the Python
worker's import path (also works when environment variables are ignored by an
embedded Windows interpreter), and disables bytecode writes. It uses the same
Python executable as the source-based agent. Optional dependencies
are **not downloaded or pip-installed automatically**. Vendor appropriately
licensed pure-Python packages, or document user-managed runtime installation.
Native wheels/binaries must match the OS and architecture. Never assume that a
package working on the author's Mac will work on Windows without testing.

## 5. Language-neutral stdio protocol

Use `runtime: "command"` and e.g. `command: ["node", "main.mjs"]` for another
language; Node must already be installed. The working directory is the package
directory. Executables are resolved using normal subprocess/PATH rules.

UTF-8 JSON objects, **one line per message**, flushed immediately. Each request
and response, including newline, is ≤65536 bytes. stdout is exclusively the
protocol; diagnostics belong on stderr. One request is in flight per worker.
The host generates a monotonically increasing integer `id`; echo it unchanged.
Unsolicited messages/events are not supported in API 1.

```json
{"id":1,"method":"initialize","params":{"api_version":1,"extension_id":"com.example.counter","platform":"win32","settings":{},"data_dir":"C:/Users/Alice/3Decks/extensions/data/com.example.counter/storage"}}
{"id":1,"result":{"api_version":1}}
{"id":2,"method":"action","params":{"action":"increment","arguments":{}}}
{"id":2,"result":{"ok":true,"message":"1"}}
{"id":3,"method":"poll","params":{}}
{"id":3,"result":{"states":{},"sources":{},"dashboards":{"counter":{"title":"Counter","cards":[{"label":"Count","value":"1"}]}}}}
{"id":4,"method":"shutdown","params":{}}
{"id":4,"result":{}}
```

Each line above is an alternating host request / program response. Errors use
`{"id":2,"error":"handler_failed"}`. The host intentionally does not expose
arbitrary protocol-error content as user-facing diagnostics. For an expected
action rejection, return `{"ok":false,"message":"Device offline"}` instead.
Action messages are truncated safely to63 UTF-8 bytes for the 3DS.

Normal RPC timeout is5 seconds. Timeout, malformed JSON, oversize output or
stdout flooding terminates the offending worker. A polling/initialization failure
sets the extension to **Needs attention**, clearing its cached contributions.
A valid action rejection does not disable it. Restart is explicit from the UI;
there is no crash/retry loop. Shutdown gets up to0.5 seconds before termination.
It is not guaranteed after a crash or force-quit.

Poll jobs use a separate pool of four host threads, so slow extension polls do
not consume the native OS collector's executor. Requests are bounded; no infinite
command queues. This isolates process crashes and protocol stalls, **not CPU,
memory, disk or subprocess consumption**. Authors must stop any child processes
they create. Untrusted packages require stronger OS isolation than API 1 provides.

## 6. Declarative console data

### Active buttons

An action declares `"state":"running"`; `poll` returns
`"states":{"running":true}`. At most32 boolean keys. The matching grid button
gets the native active appearance. Disabled/missing extensions mark their static
buttons unavailable; an attempted press explains that the PC integration needs
attention. Native pending/result animations remain shared with built-in actions.

### Generated button contents

Declare a source such as `presets`, then return:

```json
{"sources":{"presets":[
  {"id":"short","label":{"en":"5 min break","fr":"Pause 5 min"},
   "detail":"Quick break","icon":"clock","color":"#66CB10","active":false,
   "action":{"id":"start","arguments":{"minutes":5,"mode":"break"}}}
]}}
```

Only actions declared **by this extension** are allowed in its generated entries.
Arguments are validated. Stable unique entry IDs let the console send presses
back safely. A source supports32 entries; the grid shows its first6, a list shows
up to32. At the frame-size limit, the largest extension lists are shortened
fairly to keep a multi-page configuration under60,000 bytes. Do not depend on
all32 items fitting across twelve heavily populated pages.

Generated entries are not saved into config.json. Only the selected source is
saved. They are read-only in the editor, which explains where the content comes
from. Grid/list switching does not require different extension code. Disabling
the extension clears generated content. Dynamic preview data excludes action
arguments; actual execution always stays on the agent.

### Top-screen dashboards

```json
{"dashboards":{"timer":{
  "title":{"en":"Focus","fr":"Concentration"},"status":"ok",
  "cards":[
    {"label":"Remaining","value":"24:12","detail":"Current session","progress":4},
    {"label":"Completed","value":"3","detail":"Today"}
  ]
}}}
```

Up to4 cards, laid out in the native 2 × 2 area below the shared top header.
`status`: `neutral`, `ok`, `warning`, `error`. `value` is a string (≤40 UTF-8
bytes); optional progress is0–100. Localized titles/labels/details are resolved
per console language. Native buffers safely truncate title to64, label to24,
detail to64 UTF-8 bytes. Prefer short strings and supported Inter glyphs rather
than emoji. Invalid output is rejected before reaching the console.

The UI previews contributions by qualified ID, including an unsaved page's new
source/dashboard selection. Multiple consoles can display the same worker's
snapshot in different languages. Data is shared, not per-console state.

The TCP protocol stays at version1 with optional fields: configuration maps a
qualified dashboard to `dashboard: "extension"`; state contains
`extension_panels` (page id + panel) and `extension_buttons` (page/id/active/
available). Old clients ignore unknown fields; **use the updated homebrew to
display extension dashboards**. Updating the package never updates homebrew code.

## 7. Installation, trust, upgrades and recovery

The root is `extensions/` beside the agent's selected config file:

```text
extensions/
  registry.json                         enabled flags + approved SHA-256
  packages/<extension-id>/              immutable installed package
  data/<extension-id>/settings.json      host-managed settings
  data/<extension-id>/storage/           extension-managed persistent data
  trash/<extension-id>-<timestamp>/      recoverably removed packages
```

No config file path means no extension installation directory. The native file
picker selects the archive on the **computer running the agent**. HTTP extension
endpoints use the existing session token, localhost/Host and Origin protections.
The browser cannot supply executable commands or program paths to these endpoints.

Import leaves the extension disabled/untrusted. Activation explicitly approves
the installed package's fingerprint. The fingerprint is a content hash, **not a
publisher signature**. It detects changed files at rescan/start, not every
instruction executed. Refresh discovers manually added/edited packages. Editing
installed code revokes approval on refresh; re-review it before starting again.
Enabled, unchanged packages restart with the agent. Invalid packages are listed
as errors without preventing native startup. A corrupted registry fails closed
and is preserved for recovery; move/repair it then refresh and reapprove packages.

For an upgrade: disable/remove the old package, import the new one with the same
ID, then reapprove. Removal moves the package into local `trash`, keeps its data,
and leaves deck references intact. Reinstalling never restores old trust. This
is a deliberate, recoverable manual-update flow; no silent download or execution.
To restore an old package, move it from trash to `packages/<id>` while disabled,
refresh and approve. To completely erase retained settings/data, stop the agent
and remove only the specific `data/<id>` directory after backing it up.

When schemas change, keep setting keys compatible or provide documented migration
instructions. API 1 validates settings before initialization and does not run
migration/install hooks. Unknown saved fields will need manual cleanup before an
incompatible version can start. Keep published actions and arguments compatible
where possible so shared deck configurations survive upgrades.

### Troubleshooting

| Symptom | Check |
| --- | --- |
| No package listed | Archive must have extension.json at root; refresh and read import errors. |
| Review required | New/changed package; inspect author, code and hash before approving. |
| Unsupported OS | Manifest platform list. Do not fake Windows support for macOS-only scripts. |
| Runtime not found | Python agent runtime or command executable/PATH; no dependency autoinstall. |
| Needs attention | Required settings, API version, timeout, malformed output, subprocess exit. Restart after fixing. |
| Empty dynamic page | Enable package, choose its source, check poll output and save layout. |
| Generic icon | Choose a built-in icon from schema. Custom SVG is not supported. |
| No dashboard on older 3DS | Rebuild/install updated homebrew once for extension API rendering. |

To debug SDK handlers, run the extension manually with backend on `PYTHONPATH`
and send the initialize/poll/action JSON lines above on stdin. Use a temporary
data directory and non-production credentials. stderr contains traceback details;
the host drains it into a bounded in-memory tail but does not persist or expose it
through the UI (it may contain secrets). There is no public log-export API yet.

## 8. Publishing checklist and compatibility policy

- Choose a unique, stable ID; give an honest author and permission description.
- Include a README, license, support link and tested OS/architecture list.
- Keep secrets and user-specific paths out of packages and example configs.
- Use timeouts, bounded data, cached polling, stable source IDs and error results.
- Test disable/restart/remove, missing credentials, network loss and process exit.
- Run `validate`, `pack`, and import the exact resulting archive into a clean agent.
- Test both grid/list and EN/FR text; check physical 3DS legibility and Windows/macOS.
- Share the `.3deckext` archive and expected fingerprint through your chosen channel.

There is no hosted marketplace, signing authority, OAuth broker, dependency
resolver, native-code sandbox, hot code replacement, per-console worker, binary
asset streaming or push-events API in version1. These are explicit extension
points for later major/minor revisions, not implicit promises. API1 additions
should be optional; incompatible behavior requires a new API version and a
documented transition. The current host supports API1 only.

## 9. Testing the implementation

```sh
# Repository root
PYTHONPATH=agent python3 -m unittest discover -s agent/tests -p 'test_*.py' -q
ruff check agent/backend/deck3ds agent/deck3ds agent/tests
cd agent
pnpm typecheck
pnpm test:frontend
pnpm build
# Repository root, with Docker running
./build.sh
```

PowerShell equivalent: `$env:PYTHONPATH="agent"` before `python -m unittest ...`.
CI runs Python tests on Linux/macOS/Windows, frontend checks, and the devkitPro
3DS build. The extension tests use real subprocesses and temporary packages,
covering trust, lifecycle, SDK, protocol, settings redaction, safe archives,
localization and native integration without touching user files or accounts.

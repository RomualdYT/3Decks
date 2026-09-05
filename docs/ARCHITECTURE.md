# Agent architecture

[Documentation](README.md) · [Synthèse française](ARCHITECTURE.fr.md)

## Boundaries

This is a local desktop agent, not a cloud service or a multi-user web backend. See [performance measurement](PERFORMANCE.md) for repeatable local workloads and how to interpret them.

The implementation lives in `agent/backend/deck3ds`. `agent/deck3ds` is only a source-checkout import shim; the wheel installs the real package directly. `config.py` and `server.py` are compatibility facades, not alternate implementations.

| Layer | Responsibility | Dependencies |
|---|---|---|
| `api/` | FastAPI routes, HTTP models, security, static files, embedded Uvicorn | Typed services |
| `services/` | Configuration transactions, editor catalog/read models, native operations, extensions administration | Domain configuration, platform/extension contracts |
| `configuration/` | Dataclasses, shared validation, existing JSON format, atomic disk storage, location/init | Domain catalogs and extension reference syntax; no HTTP |
| `runtime/` | Native factory, explicit dependency composition, startup, supervision, signals, shutdown | Concrete implementations |
| `desktop/` | Native menu host, immutable status snapshots, single-instance handoff, login startup, GUI log | Runtime composition root and narrow OS helpers |
| `transports/` | Console TCP/UDP, handshake, actions, resolved console configuration, state publication | Explicit `AgentPort` contract |
| `platforms/` | Existing macOS/Windows integrations and owned dialog processes | Native OS facilities |
| `extensions/` | API 1 SDK, manifests, trust registry, bounded process RPC, cached contributions | No FastAPI, HTTP request or global runtime |

`AgentRuntime` composes transport collaborators. Each receives an explicit typed context; method bindings on the runtime preserve the internal transport interface while state ownership is visible in one constructor. Routes receive a frozen `Services` bundle, never the runtime. Import boundaries are checked by `tests/test_architecture.py`.

Imports do not start sockets, native collection or extension processes. `create_app()` without services is suitable for schema export and never constructs native adapters. A real runtime is built by `runtime.factory`; a failed runtime construction closes the adapter it acquired.

## Native desktop host

Installed macOS and Windows launches add one thin native host around the same
runtime. `pystray` is imported only by `desktop/tray.py`; services, transports
and HTTP have no GUI dependency. Cocoa/Win32 owns the process main thread while
`DesktopController` runs the single `asyncio` loop in one named, non-daemon
thread. Menu callbacks never block the native loop: coroutine work crosses the
boundary with `run_coroutine_threadsafe`, and browser, clipboard and filesystem
opening use short-lived background operations.

Those synchronous desktop operations admit at most four at a time. Paused
countdown changes alone do not redraw the menu. The editor suppresses overlapping
polls and ignores responses made obsolete by edits; polling pauses in hidden tabs.

The GUI receives only immutable `DesktopSnapshot` values. It cannot inspect a
client or mutate runtime state directly. Pause rejects button/value mutations
at the console command boundary while leaving TCP, discovery and collection
alive. Quick settings call `ConfigService.update_runtime_settings()`, therefore
they retain validation, revision checks, atomic replacement, in-memory install
and console publication. The React editor observes `config_revision` and only
reloads such a change when its own document is clean.

A per-configuration OS file lock prevents duplicate agents. Its adjacent state
file is private and accepts only token-bearing loopback URLs for second-launch
handoff. An unused or partially initialized runtime is still closed. Restart
and login startup use one explicit `LaunchSpec`; platform adapters own the
LaunchAgent plist or Windows `.lnk`, and uninstallers remove those artifacts.
The [desktop integration guide](DESKTOP_INTEGRATION.md) documents extension
points and native QA.

## Configuration is a document, not a rendered screen

`ConfigService.current` owns the persisted user document. `AgentRuntime.config` is a separate deep-copied console view. Generated window buttons, list entries and extension source content only mutate the latter. `configuration.serialization.to_raw()` also excludes generated contents defensively.

State reads borrow the cached console snapshot only while synchronously assembling the response; the full outgoing state is deep-copied once. That keeps native/extension state isolated without copying the same snapshot twice. The public transport snapshot accessor still returns an independent copy. HTTP response validation and per-request authentication remain active on persistent connections.

HTTP bodies are decoded without applying Pydantic defaults before domain validation. Pydantic models define output shapes and export structural input contracts (including abbreviated actions and optional sections). The same domain parser validates files, saves and preflight validation; extension contributions are checked by the existing manager.

Native action arguments are described by the same catalog consumed by the
editor. The domain parser rejects unknown fields, validates string/number types
and catalog bounds, canonicalizes hotkeys and HTTP(S) URLs, then installs the
document. Optional fields such as volume `step` remain explicit catalog
entries rather than undocumented executor behavior.

Saving and external reloads share one asynchronous lock. A save:

1. Checks the expected revision and the file fingerprint accepted with the current document.
2. Validates a private candidate, restoring `scripts` from the current document.
3. Writes UTF-8 JSON to a unique same-directory temporary, flushes/fsyncs it, and atomically replaces the file.
4. Installs the new document and resolved view only after the write succeeds.
5. Reconstructs dynamic contents and publishes the new configuration.

The accepted fingerprint is the hash of the bytes written, not a later disk read: an external edit racing after `replace()` cannot silently become the accepted document. Revision conflicts and detected external edits return 409 without writing. A failed disk write removes its temporary and preserves the previous document. A failed broadcast cannot undo a successful save.

Committed saves are separate supervised tasks, shielded from request cancellation. Shutdown drains them. External reload uses the same lock/validation/install/publication path and retains the previous document on invalid JSON. An external editor is not part of this lock; OS replacement is atomic but does not provide cross-application transactional locking. The unavoidable check/replace race with an arbitrary external writer is documented, not presented as fully preventable.

## One event loop and resource owner

`AgentRuntime.start()` starts TCP, discovery and optional HTTP, then supervises the collector and extension loop together with a stop event. Failure of a supervised background task is logged and stops the runtime. HTTP bind failure is nonfatal; TCP still runs. A browser is opened only after Uvicorn reports readiness.

Uvicorn runs through `Server.serve()` on the existing loop, with one worker, no reload, no proxy-header trust and no separate signal owner. The FastAPI lifespan tracks HTTP readiness only. Starting ASGI with several workers or starting the runtime inside lifespan would duplicate integrations and is unsupported.

TCP admission is bounded independently on both sides of authentication: at most
16 incomplete handshakes and eight authenticated consoles are retained. A
handshake has one absolute five-second deadline, including fragmented input.
Pairing failures use a one-minute sliding window (five attempts per source, 30
globally); rotating or successfully consuming the six-digit code clears the
window. These are resource and brute-force limits, not substitutes for the
durable console credential. Successful pairing creates a distinct 192-bit
bearer credential per console; the adjacent `paired-consoles.json` registry
stores only SHA-256 digests plus name and timestamps. The shared bootstrap token is not what newly paired consoles retain.
Revocation is atomic and immediately closes matching active connections.

Each authenticated client owns its locale. Action execution enters a
context-local language scope inside its worker, so two consoles cannot overwrite
one process-global translation setting while actions run concurrently. Native
actions themselves are serialized because volume and mute operations are
read/modify/write transactions over shared OS state. Extension actions remain
concurrent in their separate pool.

The runtime also keeps a bounded structured event ring and monotonic counters.
Critical TCP admission, handshake, replay and action outcomes carry stable event
names and scalar fields; `/api/state` exposes copies for local diagnosis. Human
log lines remain for compatibility. Neither representation includes console
credentials.

`runtime.signals.run_agent()` owns SIGINT/SIGTERM and restores previous handlers. Shutdown closes admissions, stops discovery and owned dialogs, drains HTTP, cancels collector/extension loops, waits for committed saves, closes clients, then drains executors and closes native resources. **TCP `wait_closed()` happens after client closure** because Python 3.12 waits for client transports too. Shutdown is idempotent; one cleanup failure is logged without skipping the remaining resources.

Admitted extension administration operations are drained before the final extension-process cleanup, so an in-flight enable cannot restart a worker after the manager has been closed. Stable module-level HTTP endpoints avoid retaining a closed application's services through framework callable caches; a garbage-collection regression test verifies factory instances are released.

## Blocking work and timeouts

`WorkPool` is lazy and bounds submitted/running work with a semaphore. Cancelling or timing out its awaiting coroutine does not release a running job's capacity; completion of the actual executor future does. Closing drains those futures before disposing the executor. Queued callers reject once a pool is stopping.

| Work | Workers | Admitted capacity |
|---|---:|---:|
| Native state/artwork collection | 2 | 4 |
| Native console actions | 1 | 8 |
| File transactions | 1 | 4 |
| Interactive system operations / OBS | 2 | 8 |
| Native dialogs | 1 | 1 |
| Extension administration | 2 | 4 |
| Extension actions | 2 | 8 |

Extension polling retains its separate four-worker pool and a registry capped at 64 packages. Each extension uses bounded stdio RPC and its own process; a timeout kills that extension, not the agent. Slow extension actions do not occupy native-action workers. State HTTP reads use cached snapshots/metadata; they never invoke native collection. Notification/capability metadata refresh is performed off-loop, at most every ten seconds.

macOS selectors use an owned `osascript` process. Windows selectors use a separate STA PowerShell process, not the persistent PowerShell session used by collection/actions. Both can be terminated during shutdown. No thread timeout is described as forcibly stopping a thread.

## Distribution boundary

The versioned Python wheel is the only maintained application package. GitHub
launchers install that exact wheel through a private `uv` tool environment and
verify its SHA-256 digest before installation. The `deck3ds-ui` GUI entry safely
creates only a missing first-run configuration and starts the local editor
without a Windows console window. User configuration and adjacent extension data
remain outside the tool environment, so upgrades and uninstall do not rewrite
them.

The Windows Store workflow consumes the already-published wheel. It adds a
private Python runtime, a minimal native launcher and the MSIX manifest needed
for package identity and `userNotificationListener`. Its output is intentionally
unsigned and is only a Partner Center submission artifact; it is never a direct
download. Microsoft signing, Store review and native permission qualification
remain outside the runtime and outside automated claims.

## HTTP and static resources

See the [HTTP reference](api/README.md) for contracts and boundary conditions. Assets live in `api/static`, built from `agent/frontend`; PNGs and fonts are packaged. Only fingerprinted `assets/` resources are immutable-cached. HTML/API use `no-store`. OpenAPI is lazy/cached and exportable without native startup. Swagger/ReDoc are disabled.

Official implementation references: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [Uvicorn programmatic serving](https://www.uvicorn.org/), [uv project layout and locking](https://docs.astral.sh/uv/concepts/projects/layout/).

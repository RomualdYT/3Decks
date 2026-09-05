# Code quality

[Documentation](README.md) · [Français](CODE_QUALITY.fr.md)

## Enforced boundaries

The HTTP layer uses typed services, not the global runtime. Configuration validation is shared by file and HTTP paths. Persisted user choices are separate from generated console content. The runtime owns sockets, admitted writes, pools, native dialogs and extension shutdown. The native menu is a host around that same runtime, not another backend.

See [architecture](ARCHITECTURE.md) for the detailed ownership and concurrency rules.

| Check | Scope |
|---|---|
| Ruff | Backend, source shim, tests and Python tools |
| Strict mypy | API, services, runtime and desktop |
| Coverage gate | 90% combined lines in those four areas; not untouched adapters or every file |
| Contract tests | HTTP, configuration transactions, TCP/UDP, pairing, extensions and lifecycle |
| Property tests | Frame fragmentation/size, URLs and pairing-code input |
| Frontend | TypeScript, Vitest, production build and OpenAPI drift |
| Distribution | Required resources, excluded personal/cache files, isolated installed-package smoke |
| Documentation | Local Markdown/HTML links checked by `tools/check_docs.py` |

The dated results and unperformed native checks live in [Qualification](QUALIFICATION.md), avoiding duplicated test counts here.

## Maintainability priorities

Keep modules focused on a responsibility. Around 400 lines is a review trigger, not a rule to split coherent code artificially. Native macOS/Windows adapters and extension orchestration remain the main areas to inspect when adding behavior.

Prefer narrow composition to broad shared mutable contexts. Do not introduce generic layers without a concrete consumer. Keep platform behavior testable without claiming simulated calls prove actual OS permission support.

Recent guards protect editor edits against stale HTTP responses, bound desktop background work, preserve media preferences and rotate logs without restart. Hidden tabs suspend polling and pause countdown changes do not repeatedly rebuild the menu.

## Performance discipline

Measure idle cost, action latency, reconnect reliability and resource cleanup before optimizing throughput. State HTTP reads use cached snapshots, not native collection; one outgoing deep copy preserves isolation. Native/extension/interactive work uses separate bounded capacities.

FastAPI adds measurable overhead in the initial loopback benchmark. See [local-app tradeoffs](LOCAL_APP.md) and the raw qualification data rather than treating the framework as a speed optimization.

## Contributor workflow

Use the [development commands](CONTRIBUTING_AGENT.md), [documentation index](README.md) and [release checklist](PUBLIC_RELEASE.md). Keep behavior changes, regression tests and documentation together.

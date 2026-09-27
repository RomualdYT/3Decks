# Testing 3Decks

[Documentation](README.md) · [Français](TESTING.fr.md)

Tests describe the application's supported behavior, not the steps used to build it.

## Run the checks

From `agent/`:

```sh
uv sync --locked
uv run --locked pytest --cov --cov-report=term-missing
uv run --locked ruff check backend/deck3ds deck3ds tests tools
uv run --locked mypy
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:frontend
pnpm api:check
pnpm build
uv build
uv run --locked python tools/qualify_wheel.py
```

From the root:

```sh
python3 tools/check_docs.py
python3 -m unittest discover -s tools -p test_check_docs.py
bash tools/test_console.sh
./build.sh
```

Console builds need Docker or local devkitPro. The wheel smoke test installs into a temporary environment outside the checkout, so packaging mistakes cannot be hidden by source imports.

## Test responsibilities

| Area | Files in `agent/tests/` | Contract |
|---|---|---|
| Editor HTTP | `test_api_*.py` | Authenticated routes, status codes, JSON, headers, conflicts and static assets |
| Catalog and config | `test_catalog.py`, `test_configuration.py`, `test_config_transactions.py` | Available actions, FR/EN labels, limits, validation and durable writes |
| Lifecycle and services | `test_runtime.py`, `test_services.py`, `test_state_reads.py` | Resource ownership, cached reads and bounded work |
| Console | `test_tcp.py`, `test_protocol.py`, `test_discovery.py`, `test_transport_actions.py` | Framing, handshake, pairing, language, actions and disconnection |
| OS adapters | `test_macos*.py`, `test_windows*.py`, `test_platforms.py`, `test_native_dialogs.py` | Native command construction and result interpretation using controlled providers |
| Desktop | `test_desktop*.py` | Menu state, instance lock, quick settings, shutdown and log bounds |
| Extensions | `test_extensions.py` | Package validation, approval, subprocess RPC, contributions and cleanup |
| Release/tooling | `test_release_distribution.py`, `test_public_config.py`, `test_benchmark_tools.py` | Artifact boundaries, neutral sample and usable benchmark reports |
| Architecture | `test_architecture.py` | Actual import boundaries, including relative/absolute imports |

Frontend behavior belongs in Vitest beside the relevant React hook/component or utility. A Python assertion about a string in a React source file is not evidence that an interaction works. Data catalogs and generated contracts may still require cross-component consistency checks.

The native console suite in `3ds-app/tests/` runs production C logic on macOS/Linux with sanitizers and loopback sockets. It covers frame boundaries, deadlines, protocol/UTF-8, navigation, touch geometry, feedback and text cache eviction. SDK stubs do not emulate GPU or physical console behavior. See [console architecture](CONSOLE_ARCHITECTURE.md).

## Isolation and safety

Use fake platforms, temporary files, loopback sockets and controlled subprocesses. Never use your personal config, launch applications, alter permissions or send commands to a real console in the default test suite. Synthetic secrets and paths are explicit fixtures, not credentials to redact from test expectations.

Use pytest's standard output capture; do not suppress failures to make CI look clean. Tests that assert log behavior capture their output. Benchmarks emit machine-readable results without personal configuration.

Keep supported compatibility behavior covered while it remains part of the code. Avoid tests that only assert deleted modules stay deleted, exact formatting, historical file sizes or explanatory comments. Prefer returned values, observable state and resource cleanup.

## Test quality

Each test should establish one contract with a descriptive name, arrange its input, perform the operation and assert the result. Parameterize meaningful variants. Match stable error codes where available rather than incidental wording; assert exact FR/EN text only when localization is the contract.

Teardown must run even on failure. A thread timeout is not proof that the thread stopped. Noisy real-OS permission and end-to-end console checks belong in the explicit [native qualification checklist](QUALIFICATION.md), not unattended CI.

The combined API/services/runtime/desktop coverage threshold remains 90%. Coverage and case counts help detect gaps; neither replaces meaningful assertions. Do not lower the gate to accommodate a test reorganization.

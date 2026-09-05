# Qualification evidence

[Documentation](README.md) · [Français](QUALIFICATION.fr.md) · [Release checklist](PUBLIC_RELEASE.md)

## Latest completed stabilization pass — 5 September 2026

Results below refer to the code tested in that pass, not an automatically updated badge for all future commits. Documentation changes do not constitute a new native qualification.

| Check | Observed result and scope |
|---|---|
| Python | 533 tests and 80 subtests passed locally on macOS, Python 3.12 |
| Coverage | 91.92% combined line coverage for API/services/runtime/desktop; configured gate 90%, not a per-file claim |
| Static quality | Ruff passed; strict mypy passed on 38 modules |
| Frontend | 17 Vitest tests, TypeScript check and production build passed |
| Contracts | OpenAPI export and generated TypeScript checks passed |
| Distribution | Wheel/sdist built; isolated wheel installation exercised CLI, static assets, HTTP, TCP and an example extension outside checkout |
| Desktop | Real macOS menu process started with temporary config; UI readiness, cooperative CLI shutdown and lock cleanup verified |
| Public sample | Current config plus five historical versions checked: no nonempty credentials/personal paths in the inspected categories |
| Remote CI | Workflow configured; no complete remote matrix run claimed by this local pass |
| Windows | Simulated contracts checked locally; native Windows/MSIX qualification remains outstanding |

Regression coverage includes slow HTTP responses preserving edits, hidden-tab polling, media preference retention, Windows-without-`fchmod` behavior, continuous UTF-8 log rotation, bounded background admission, tray redraw suppression and cooperative stop timeout behavior. Existing tests also cover HTTP boundaries, transactional saves, owned subprocess shutdown, real Uvicorn/TCP/UDP with fake adapters, pairing/revocation, action validation and extensions.

## Short endurance scenario

The latest 30-second run used a fake native adapter, temporary configuration and slow off-loop work: **183 TCP reconnects, 9 saves, 0.89 ms maximum ping**, 0.201 MiB traced allocation growth and 0.594 MiB traced peak. No `3decks-` worker remained after closure; total process threads were two.

This is not a four-hour endurance run, total RSS measurement, real 3DS Wi-Fi measurement or native media performance result.

From `agent/`, without concurrent builds/tests:

```sh
uv run --locked python tools/endurance_agent.py --duration 30 --slow-action-ms 100 --quiet
```

The tool defaults to four hours when duration is omitted. Do not claim that duration unless it was actually run.

## Historical migration measurements

Raw data remains in [initial FastAPI comparison](performance/fastapi-2026-08-31.json) and [populated-state comparison](performance/local-state-2026-08-31.json). These are different scenarios; do not compare their timings directly.

The initial comparison used the same computer/interpreter, four concurrent clients, 400 HTTP reads and 100 TCP pings per cycle, across five cycles, with a new HTTP connection per request and no native integrations:

| Metric | Historical HTTP server | FastAPI |
|---|---:|---:|
| First HTTP startup including import | 1.28 ms | 198.42 ms |
| Later startup | 0.38–0.55 ms | 1.29–1.84 ms |
| Median of per-cycle HTTP medians | 0.785 ms | 1.500 ms |
| Median of per-cycle HTTP p95 | 1.008 ms | 1.803 ms |
| Median of per-cycle TCP ping p95 | 0.510 ms | 0.874 ms |
| Tasks remaining after shutdown | 0 | 0 |

These are not aggregated percentiles. **FastAPI was not faster in this scenario.** Its measured cost buys typed contracts, maintainable HTTP handling and resource lifecycle separation, not an automatic speedup.

A separate instrumented five-cycle run retained 18.742 to 18.763 MiB of Python allocations after collection, following a fix for application retention by framework callable caches. These are not RSS figures; imports and caches legitimately remain. Full cycle values are retained in the raw data.

## Reproduce other scenarios

```sh
# From agent/
uv run --locked python tools/benchmark_runtime.py
uv run --locked python tools/benchmark_runtime.py --trace-memory
uv run --locked python tools/benchmark_runtime.py --populated --keep-alive
uv run --locked python -m tools.benchmark_state
```

The historical comparison requires exporting commit `598cd0a` into a temporary source directory and passing `--historical-source` to the benchmark. The installed agent contains no old HTTP backend.

## Native checklist before release

- [ ] Run the full remote OS/Python matrix on the candidate commit.
- [ ] Install the release artifact on macOS and Windows; inspect every editor view, fonts, console PNG and responsive layout.
- [ ] Create/save/reload controls, test conflicts, keyboard capture, page drag-and-drop and menu quick settings.
- [ ] Test permissions on the actual distributed macOS interpreter: Automation, Accessibility, notifications, Spotify/Music, dialogs and OBS.
- [ ] Test Windows native actions/media/dialogs and MSIX notification refusal then consent.
- [ ] Test real 3DS discovery, pairing/revocation, FR/EN state, actions, sleep/wake and reconnection.
- [ ] Import/review/enable/configure/remove an example extension and verify its console display.
- [ ] Stop during a save, open dialog and slow extension; check remaining native processes.
- [ ] Check login startup, second launch, restart, update, uninstall and rollback with backed-up data.

Earlier targeted browser and native checks are not substitutes for this complete release pass. Dependency audits also expire: rerun them for the candidate; no current vulnerability-free guarantee is made here.

# Measure performance

[Documentation](README.md) · [Français](PERFORMANCE.fr.md)

3Decks is a local desktop agent. Priorities are low idle cost, responsive actions, stable reconnection and complete shutdown. HTTP throughput alone is not a useful product score.

## Repeatable scenarios

From `agent/`, without simultaneous builds or other benchmarks:

```sh
uv run --locked python -m tools.benchmark_state
uv run --locked python tools/benchmark_runtime.py --cycles 5 --requests 400 --populated --keep-alive
uv run --locked python tools/benchmark_runtime.py --cycles 5 --requests 400 --trace-memory
uv run --locked python tools/endurance_agent.py --duration 30 --slow-action-ms 100 --quiet
```

- State preparation isolates cached response construction from the network.
- Runtime measurement combines real loopback HTTP/TCP with synthetic desktop state and records startup, request/ping latency, loop delay and remaining resources.
- Memory tracing is a separate instrumented run. Python allocations are not total process RAM (RSS), and instrumentation changes timings.
- Endurance exercises reconnects, saves and slow off-loop work. Duration defaults to four hours; specify a short duration for a smoke check.

These tools exercise the current implementation only. The runtime report is JSON on stdout and uses no personal config, native collection or real extension account.

## Interpret results honestly

### Console text-layout workload

Run `bash tools/test_console.sh` from the repository root. Its text-layout test
uses a deterministic character-width callback: the first clipped label requires
seven measurements, and 10,000 identical repeats require no additional
measurements. Eviction, changed width/scale, long strings, UTF-8 and reset are
checked separately. This measures eliminated layout work, not GPU text parsing,
real font timing or FPS. The bounded caches reserve approximately 22 KiB.

On physical hardware, compare the same page, language, media title, console
model and stereo setting. Inspect touch responsiveness during large snapshots,
artwork bursts and reconnects. Host sanitizers and cross-build success do not
measure battery life, Wi-Fi latency or frame rate. See
[console architecture](CONSOLE_ARCHITECTURE.md) for the per-frame limits.

### Agent measurements

Record commit, OS/interpreter, workload, connection mode and whether tracing was active. Compare identical workloads and retain outliers. Per-cycle percentiles are not pooled percentiles.

Do not turn a short run into a long-term endurance claim. Loopback timing does not predict 3DS Wi-Fi or native Spotify/OBS latency. Tests verify report structure and cleanup, not fixed timing thresholds that depend on CI load.

For release qualification, also inspect CPU/RAM at idle with the actual shipped interpreter and enabled integrations. Preserve local HTTP security and resource limits while optimizing. See [architecture](ARCHITECTURE.md) and [native checks](QUALIFICATION.md).

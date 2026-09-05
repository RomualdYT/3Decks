# Local application design and performance

[Documentation](README.md) · [Français](LOCAL_APP.fr.md)

3Decks is one local desktop agent, one asyncio runtime and a console connection on the LAN. FastAPI is embedded for the editor, not a separate service users administer. No cloud account, application database, Redis or multi-worker server is required. Extension/dialog subprocesses are owned resources.

The native menu keeps the GUI on the main thread and runs the one asyncio loop on a dedicated thread. Quick settings use the same transactional service as HTTP. A native webview could be added later, but the current editor is a browser page.

## Optimize what users experience

Idle cost, native action latency, reconnection and clean shutdown matter more than peak HTTP throughput. Keep slow native work off the event loop, preserve local HTTP protections and avoid duplicating agents to support a UI.

The state service now borrows a cached internal snapshot and performs one complete outgoing deep copy instead of two. Public snapshot access still returns an independent copy. Response validation remains active; no stale timed HTTP cache was introduced.

## Historical populated-state benchmark

[Full measurements](performance/local-state-2026-08-31.json), macOS arm64/Python 3.12.12. Synthetic state: 11,075 bytes, apps/audio/notifications/media/logs and extension previews; no real native adapter or extension process.

Seven batches of 1,000 reads measured state preparation. Network tests used five cycles of 400 HTTP reads, four clients and 100 TCP pings. Values below are medians of per-cycle metrics, not global percentiles.

| Measurement | Before | After |
|---|---:|---:|
| State preparation only | 323.356 µs | 283.992 µs |
| Persistent HTTP median | 2.666 ms | 2.527 ms |
| Persistent HTTP typical p95 | 3.485 ms | 3.387 ms |
| New-connection HTTP median | 3.116 ms | 3.228 ms |
| New-connection HTTP typical p95 | 3.902 ms | 3.714 ms |
| TCP ping p95 under persistent HTTP | 2.977 ms | 2.780 ms |
| TCP ping p95 under new connections | 0.545 ms | 1.403 ms |
| Event-loop lag p95, persistent HTTP | 1.284 ms | 1.544 ms |
| Event-loop lag p95, new connections | 1.835 ms | 1.563 ms |
| Tasks after shutdown | 0 | 0 |
| Threads after shutdown | 1 | 1 |

Isolated state preparation improved about 12.2%. Network differences are modest and some regress; **this does not establish a general speedup**. Keepalive already worked before the change. This test is neither actual editor polling nor 3DS Wi-Fi. Do not directly compare it with the minimal-state [initial migration scenario](QUALIFICATION.md); traced allocations are not total RAM use.

## Reproduce

From `agent/`, without other benchmarks/builds running:

```sh
uv run --locked python -m tools.benchmark_state
uv run --locked python tools/benchmark_runtime.py --populated
uv run --locked python tools/benchmark_runtime.py --populated --keep-alive
```

These tools use synthetic data, not your personal running agent. Cross-platform simulation is not a Windows native measurement.

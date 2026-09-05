"""Repeatable loopback benchmark; never loads user config or native adapters."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import threading
import time
import tracemalloc
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deck3ds.config import Config, PageConfig
from deck3ds.platforms.base import Platform
from deck3ds.server import Server


async def measure(label: str, count: int) -> dict:
    tracemalloc.start()
    started = time.perf_counter()
    agent = Server(Config(pages=[PageConfig("main")]), Platform())
    agent.local_addresses = lambda: ["127.0.0.1:38123"]
    from deck3ds.api.server import UiServer

    ui = UiServer(agent.services, port=0)
    await ui.start()
    startup_ms = (time.perf_counter() - started) * 1000
    port = ui.port or ui._server.sockets[0].getsockname()[1]
    latencies: list[float] = []
    lags: list[float] = []
    running = True

    async def heartbeat():
        while running:
            before = time.perf_counter()
            await asyncio.sleep(0.005)
            lags.append(max(0, time.perf_counter() - before - 0.005) * 1000)

    async def request():
        before = time.perf_counter()
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(
            (
                f"GET /api/state HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                f"X-Deck3DS-Token: {ui.token}\r\nConnection: close\r\n\r\n"
            ).encode()
        )
        await writer.drain()
        response = await reader.read()
        writer.close()
        await writer.wait_closed()
        assert response.startswith(b"HTTP/1.1 200"), response[:100]
        latencies.append((time.perf_counter() - before) * 1000)

    ticker = asyncio.create_task(heartbeat())
    try:
        for _ in range(10):
            await request()
        latencies.clear()
        for _ in range(count // 4):
            await asyncio.gather(*(request() for _ in range(4)))
    finally:
        running = False
        await ticker
        await ui.close()
        if hasattr(agent, "close"):
            await agent.close()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    def p95(values):
        return sorted(values)[min(len(values) - 1, int(len(values) * 0.95))]

    return {
        "label": label,
        "requests": len(latencies),
        "concurrency": 4,
        "python": sys.version.split()[0],
        "startup_ms": round(startup_ms, 2),
        "http_median_ms": round(statistics.median(latencies), 2),
        "http_p95_ms": round(p95(latencies), 2),
        "event_loop_p95_ms": round(p95(lags), 2),
        "traced_current_mib": round(current / 1024**2, 2),
        "traced_peak_mib": round(peak / 1024**2, 2),
        "threads_after_close": threading.active_count(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="fastapi")
    parser.add_argument("--requests", type=int, default=400)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(measure(args.label, args.requests)), indent=2))

"""TCP ping under HTTP load and repeated lifecycle measurements, on fake OS data.

Runs only the current agent with synthetic data; no user configuration is read.
"""

from __future__ import annotations
import argparse
import asyncio
import gc
import json
import statistics
import sys
import threading
import time
import tracemalloc
from pathlib import Path


def p95(values: list[float]) -> float:
    return sorted(values)[min(len(values) - 1, int(len(values) * 0.95))]


async def cycle(
    samples: int, keep_alive: bool = False, populated: bool = False
) -> dict:
    from deck3ds.config import Config, PageConfig
    from deck3ds.platforms.base import Platform
    from deck3ds.runtime.agent import AgentRuntime
    from deck3ds import protocol

    started = time.perf_counter()
    agent = AgentRuntime(Config(pages=[PageConfig("main")]), Platform())
    # Keep synthetic diagnostics in memory; stdout is one machine-readable report.
    agent.logs._append_line = agent._logs.append
    if populated:
        from tools.benchmark_data import populate

        populate(agent)
    from deck3ds.api.server import UiServer

    ui = UiServer(agent.services, port=0)
    listener = agent._server = await asyncio.start_server(
        agent._handle_client, "127.0.0.1", 0
    )
    await ui.start()
    ui_port = ui.port
    startup = 1000 * (time.perf_counter() - started)
    reader, writer = await asyncio.open_connection(
        "127.0.0.1", listener.sockets[0].getsockname()[1]
    )
    frames = protocol.FrameReader()
    http_times, ping_times, lags = [], [], []
    response_sizes = []
    http_connections = 0
    alive = True

    async def receive(kind):
        while True:
            for message in frames:
                if message.get("type") == kind:
                    return message
            data = await asyncio.wait_for(reader.read(65536), 2)
            assert data
            frames.feed(data)

    writer.write(
        protocol.encode({"type": "hello", "protocol": 1, "device": "benchmark"})
    )
    await writer.drain()
    await receive("config.snapshot")

    async def requests():
        nonlocal http_connections
        http_writer = None
        connection = "keep-alive" if keep_alive else "close"
        request = (
            f"GET /api/state HTTP/1.1\r\nHost: 127.0.0.1:{ui_port}\r\nX-Deck3DS-Token: {ui.token}\r\nConnection: {connection}\r\n\r\n"
        ).encode()
        try:
            for _ in range(samples // 4):
                before = time.perf_counter()
                if http_writer is None:
                    http_reader, http_writer = await asyncio.open_connection(
                        "127.0.0.1", ui_port
                    )
                    http_connections += 1
                http_writer.write(request)
                await http_writer.drain()
                headers = await asyncio.wait_for(http_reader.readuntil(b"\r\n\r\n"), 2)
                assert headers.startswith(b"HTTP/1.1 200"), headers[:100]
                fields = dict(
                    line.lower().split(b":", 1)
                    for line in headers.split(b"\r\n")[1:]
                    if b":" in line
                )
                size = int(fields[b"content-length"])
                await asyncio.wait_for(http_reader.readexactly(size), 2)
                response_sizes.append(size)
                if not keep_alive:
                    http_writer.close()
                    await http_writer.wait_closed()
                    http_writer = None
                http_times.append(1000 * (time.perf_counter() - before))
        finally:
            if http_writer is not None:
                http_writer.close()
                await http_writer.wait_closed()

    async def pings():
        for _ in range(100):
            before = time.perf_counter()
            writer.write(protocol.encode({"type": "ping"}))
            await writer.drain()
            await receive("pong")
            ping_times.append(1000 * (time.perf_counter() - before))
            await asyncio.sleep(0.001)

    async def heartbeat():
        while alive:
            before = time.perf_counter()
            await asyncio.sleep(0.002)
            lags.append(max(0, time.perf_counter() - before - 0.002) * 1000)

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        await asyncio.gather(pings(), *(requests() for _ in range(4)))
    finally:
        alive = False
        await heartbeat_task
        writer.close()
        await writer.wait_closed()
        await ui.close()
        await agent.close()
        await asyncio.sleep(0)
    return {
        "startup_ms": round(startup, 2),
        "http_median_ms": round(statistics.median(http_times), 3),
        "http_p95_ms": round(p95(http_times), 3),
        "ping_median_ms": round(statistics.median(ping_times), 3),
        "ping_p95_ms": round(p95(ping_times), 3),
        "event_loop_p95_ms": round(p95(lags), 3),
        "http_connections": http_connections,
        "response_bytes": max(response_sizes),
        "threads_after_close": threading.active_count(),
        "tasks_after_close": len(asyncio.all_tasks()) - 1,
    }


async def measure(
    cycles: int,
    samples: int,
    trace_memory: bool = False,
    keep_alive: bool = False,
    populated: bool = False,
) -> dict:
    if trace_memory:
        tracemalloc.start()
    results = []
    for _ in range(cycles):
        result = await cycle(samples, keep_alive, populated)
        if trace_memory:
            gc.collect()
            current, peak = tracemalloc.get_traced_memory()
            result["traced_current_mib"] = round(current / 1024**2, 3)
            result["traced_peak_mib"] = round(peak / 1024**2, 3)
        results.append(result)
    if trace_memory:
        tracemalloc.stop()
    return {
        "scenario": "current-agent-http-tcp",
        "python": sys.version.split()[0],
        "http_requests_per_cycle": samples,
        "pings_per_cycle": 100,
        "trace_memory": trace_memory,
        "connection": "keep-alive" if keep_alive else "close",
        "payload": "populated" if populated else "minimal",
        "cycles": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--requests", type=int, default=400)
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="Four persistent HTTP connections, as a browser can reuse",
    )
    parser.add_argument(
        "--populated",
        action="store_true",
        help="Synthetic desktop state and four cached extension previews",
    )
    parser.add_argument(
        "--trace-memory",
        action="store_true",
        help="Separate instrumented run; changes timings, Python allocations are not RSS",
    )
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if args.cycles < 1 or args.requests < 4 or args.requests % 4:
        parser.error(
            "At least one cycle and a positive multiple of four HTTP requests are required"
        )
    print(
        json.dumps(
            asyncio.run(
                measure(
                    args.cycles,
                    args.requests,
                    args.trace_memory,
                    args.keep_alive,
                    args.populated,
                )
            ),
            indent=2,
        )
    )

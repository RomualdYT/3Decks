"""Bounded endurance scenario for reconnects, saves and slow off-loop work.

Default run: four hours. For a qualification smoke run:
    uv run python -m tools.endurance_agent --duration 2 --slow-action-ms 10
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import socket
import tempfile
import threading
import time
import tracemalloc
from pathlib import Path

from deck3ds import config, protocol
from deck3ds.configuration.location import initialize
from deck3ds.platforms.base import Platform
from deck3ds.runtime.agent import AgentRuntime
from deck3ds.transports.parts import Options


def available_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


async def receive(
    reader: asyncio.StreamReader, frames: protocol.FrameReader, kind: str
) -> dict:
    while True:
        for message in frames:
            if message.get("type") == kind:
                return message
        data = await asyncio.wait_for(reader.read(65536), 3)
        if not data:
            raise RuntimeError(f"connection closed before {kind}")
        frames.feed(data)


async def run(args: argparse.Namespace) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="3decks-endurance-") as directory:
        root = Path(directory)
        path = root / "config.json"
        initialize(path)
        loaded = config.load(path)
        loaded.host, loaded.port = "127.0.0.1", available_port()
        config.save(loaded, path)
        agent = AgentRuntime(
            loaded,
            Platform(),
            Options(config_path=path, ui_port=None),
        )

        async def no_discovery() -> None:
            return None

        agent._start_discovery = no_discovery
        if args.quiet:
            agent.logs._append_line = lambda _message: None

        tracemalloc.start()
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0]
        runtime = asyncio.create_task(agent.start(), name="endurance-runtime")
        iterations = saves = 0
        durable_token = loaded.token
        peak_ping_ms = 0.0
        started = time.monotonic()
        try:
            for _ in range(600):
                if runtime.done():
                    await runtime
                    raise RuntimeError("agent stopped during endurance startup")
                if agent._tasks:
                    break
                await asyncio.sleep(0.01)
            else:
                raise RuntimeError("agent startup timed out")

            while iterations == 0 or time.monotonic() - started < args.duration:
                reader, writer = await asyncio.open_connection(
                    "127.0.0.1", loaded.port
                )
                frames = protocol.FrameReader()
                writer.write(
                    protocol.encode(
                        {
                            "type": "hello",
                            "protocol": 1,
                            "device": "endurance-3ds",
                            "language": "en",
                            "token": durable_token,
                        }
                    )
                )
                await writer.drain()
                hello = await receive(reader, frames, "hello.ok")
                durable_token = str(hello.get("token") or durable_token)
                await receive(reader, frames, "config.snapshot")

                # Slow work remains on its dedicated executor while TCP ping
                # demonstrates that the asyncio loop stays responsive.
                slow = asyncio.create_task(
                    agent.extension_actions_pool.run(
                        time.sleep, args.slow_action_ms / 1000
                    )
                )
                ping_started = time.monotonic()
                writer.write(protocol.encode({"type": "ping", "id": iterations + 1}))
                await writer.drain()
                await receive(reader, frames, "pong")
                peak_ping_ms = max(
                    peak_ping_ms, (time.monotonic() - ping_started) * 1000
                )
                await slow
                writer.close()
                await writer.wait_closed()

                iterations += 1
                if iterations % args.save_every == 0:
                    document = agent.services.config.document()["config"]
                    await agent.services.config.save(document)
                    saves += 1
                await asyncio.sleep(args.reconnect_delay)
        finally:
            agent.request_stop()
            await asyncio.wait_for(runtime, 10)

        gc.collect()
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        growth_mib = (current_memory - baseline_memory) / 1024**2
        if growth_mib > args.max_memory_growth_mib:
            raise RuntimeError(
                f"traced memory growth {growth_mib:.2f} MiB exceeds "
                f"{args.max_memory_growth_mib:.2f} MiB"
            )
        leaked = [
            thread.name
            for thread in threading.enumerate()
            if thread.name.startswith("3decks-")
        ]
        if leaked:
            raise RuntimeError(f"agent worker thread leaked after shutdown: {leaked}")
        return {
            "duration_seconds": round(time.monotonic() - started, 2),
            "iterations": iterations,
            "configuration_saves": saves,
            "peak_ping_ms_during_slow_work": round(peak_ping_ms, 2),
            "traced_memory_growth_mib": round(growth_mib, 3),
            "traced_memory_peak_mib": round(peak_memory / 1024**2, 3),
            "threads_after_close": threading.active_count(),
            "counters": agent.event_counters(),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=4 * 60 * 60)
    parser.add_argument("--reconnect-delay", type=float, default=0.05)
    parser.add_argument("--save-every", type=int, default=20)
    parser.add_argument("--slow-action-ms", type=float, default=100)
    parser.add_argument("--max-memory-growth-mib", type=float, default=16)
    parser.add_argument("--quiet", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    if (
        args.duration <= 0
        or args.reconnect_delay < 0
        or args.save_every < 1
        or args.slow_action_ms < 0
        or args.max_memory_growth_mib <= 0
    ):
        parser.error("durations, save interval and memory limit must be positive")
    print(json.dumps(asyncio.run(run(args)), indent=2))


if __name__ == "__main__":
    main()

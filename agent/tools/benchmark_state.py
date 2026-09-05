"""Isolate populated state-read cost: seven rounds, 1,000 reads per round.

Run from agent/: uv run --locked python -m tools.benchmark_state
No HTTP, native collection, configuration file or real extension is used.
"""

import asyncio
import json
import statistics
import time

from deck3ds.config import Config, PageConfig
from deck3ds.platforms.base import Platform
from deck3ds.runtime.agent import AgentRuntime
from .benchmark_data import populate


async def measure() -> dict:
    agent = AgentRuntime(Config(pages=[PageConfig("main")]), Platform())
    populate(agent)
    samples = []
    try:
        for _ in range(7):
            started = time.perf_counter()
            for _ in range(1000):
                agent.services.state.read()
            samples.append(round((time.perf_counter() - started) * 1000, 3))
    finally:
        await agent.close()
    return {
        "reads_per_round": 1000,
        "rounds_us_per_read": samples,
        "median_us": statistics.median(samples),
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(measure()), indent=2))

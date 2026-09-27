"""One signal owner for both headless and HTTP runs, including Windows."""

from __future__ import annotations

import asyncio
import signal
import threading
from types import FrameType

from .agent import AgentRuntime


async def run_agent(agent: AgentRuntime) -> None:
    loop = asyncio.get_running_loop()
    previous: dict[signal.Signals, signal._HANDLER] = {}

    def stop(_signum: int, _frame: FrameType | None) -> None:
        loop.call_soon_threadsafe(agent.request_stop)

    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, stop)
    try:
        await agent.start()
    finally:
        try:
            await agent.close()
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)

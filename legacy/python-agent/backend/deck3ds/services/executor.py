"""Bounded off-loop work; cancellation never releases a running job's slot."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


class WorkPool:
    def __init__(self, name: str, workers: int = 4, capacity: int = 8) -> None:
        self._name = name
        self._workers = workers
        self._slots = asyncio.Semaphore(capacity)
        self._pool: ThreadPoolExecutor | None = None
        self._pending: set[asyncio.Future[Any]] = set()
        self._closing = False

    async def run(
        self, function: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        if self._closing:
            raise RuntimeError("Service is stopping")
        await self._slots.acquire()
        if self._closing:
            self._slots.release()
            raise RuntimeError("Service is stopping")
        if self._pool is None:
            self._pool = ThreadPoolExecutor(
                self._workers, thread_name_prefix=self._name
            )
        try:
            future = asyncio.get_running_loop().run_in_executor(
                self._pool, partial(function, *args, **kwargs)
            )
        except BaseException:
            self._slots.release()
            raise
        self._pending.add(future)

        def finished(completed: asyncio.Future[T]) -> None:
            self._pending.discard(completed)
            self._slots.release()
            if not completed.cancelled():
                completed.exception()  # observe failures after caller cancellation

        future.add_done_callback(finished)
        return await asyncio.shield(future)

    async def close(self, finalizer: Callable[[], None] | None = None) -> None:
        self._closing = True
        if self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)
        try:
            if finalizer is not None:
                if self._pool is None:
                    self._pool = ThreadPoolExecutor(
                        self._workers, thread_name_prefix=self._name
                    )
                await asyncio.get_running_loop().run_in_executor(self._pool, finalizer)
        finally:
            if self._pool is not None:
                self._pool.shutdown(wait=True, cancel_futures=True)
                self._pool = None

"""Embedded single-worker Uvicorn, without its own signal or event-loop owner."""

from __future__ import annotations
import asyncio
import socket
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator
import uvicorn
from ..services.bundle import Services
from .app import create_app
from .security import HttpSettings, MAX_HEADER


class EmbeddedServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config) -> None:
        super().__init__(config)
        self.ready = asyncio.Event()

    @contextmanager
    def capture_signals(self) -> Iterator[None]:
        # The CLI owns process signals, including the headless case.
        yield

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        try:
            await super().startup(sockets)
        except SystemExit as error:
            raise RuntimeError("HTTP startup failed") from error
        if self.started:
            self.ready.set()


class UiServer:
    def __init__(
        self,
        services: Services,
        port: int = 38124,
        log: Callable[[str], None] | None = None,
        static_root: Path | None = None,
        dev_origins: tuple[str, ...] = (),
    ) -> None:
        self.services, self.port = services, port
        self.log = log or (lambda _: None)
        self.static_root = static_root or Path(__file__).with_name("static")
        self.dev_origins = dev_origins
        self.token = HttpSettings().token
        self._socket: socket.socket | None = None
        self._uvicorn: EmbeddedServer | None = None
        self._task: asyncio.Task[None] | None = None
        self._server: asyncio.Server | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/?token={self.token}"

    @property
    def running(self) -> bool:
        return (
            self._task is not None
            and not self._task.done()
            and self._server is not None
        )

    async def start(self) -> None:
        if self._socket is not None:
            raise RuntimeError("HTTP server already started")
        sock = self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if sys.platform == "win32":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", self.port))
            sock.setblocking(False)
            self.port = sock.getsockname()[1]
            app = create_app(
                self.services,
                HttpSettings(self.port, self.token, self.dev_origins),
                self.static_root,
                self.log,
            )
            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=self.port,
                workers=1,
                loop="asyncio",
                http="h11",
                ws="none",
                lifespan="on",
                log_config=None,
                access_log=False,
                server_header=False,
                proxy_headers=False,
                limit_concurrency=64,
                timeout_keep_alive=5,
                timeout_graceful_shutdown=2,
                h11_max_incomplete_event_size=MAX_HEADER,
            )
            self._uvicorn = server = EmbeddedServer(config)
            self._task = asyncio.create_task(
                server.serve(sockets=[sock]), name="agent-http"
            )
            ready = asyncio.create_task(server.ready.wait())
            try:
                done, _ = await asyncio.wait(
                    (self._task, ready), timeout=10, return_when=asyncio.FIRST_COMPLETED
                )
                if self._task in done:
                    await self._task
                    raise RuntimeError("HTTP server exited during startup")
                if ready not in done:
                    raise RuntimeError("HTTP startup timed out")
                self._server = server.servers[0]
            finally:
                ready.cancel()
                await asyncio.gather(ready, return_exceptions=True)
        except BaseException:
            await self.close()
            raise

    def stop_admissions(self) -> None:
        if self._uvicorn:
            self._uvicorn.should_exit = True
        if self._server:
            self._server.close()

    async def close(self) -> None:
        self.stop_admissions()
        if self._task:
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=4)
            except (TimeoutError, asyncio.CancelledError):
                self._task.cancel()
                await asyncio.gather(self._task, return_exceptions=True)
            except Exception:
                pass
        if self._socket:
            self._socket.close()
        self._socket = None
        self._server = None

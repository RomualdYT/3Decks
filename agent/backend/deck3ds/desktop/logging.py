"""Durable output for GUI launches, including console-less Windows starts."""

from __future__ import annotations

import io
import logging
from logging.handlers import RotatingFileHandler
import sys
import threading
from pathlib import Path
from typing import TextIO, Protocol

from platformdirs import user_log_path


MAX_LOG_SIZE = 2 * 1024 * 1024


def desktop_log_path() -> Path:
    return user_log_path("3Decks", appauthor=False) / "agent.log"


class RotatingLog(io.TextIOBase):
    """One shared handler serializes stdout/stderr and rotates while running."""

    def __init__(self, path: Path) -> None:
        self.handler = RotatingFileHandler(path, maxBytes=MAX_LOG_SIZE, backupCount=1, encoding="utf-8")
        self.handler.terminator = ""

    def write(self, value: str) -> int:
        # Bound even a single unexpectedly large print. Four bytes per Unicode
        # character covers UTF-8 without cutting a multibyte sequence in half.
        for start in range(0, len(value), max(1, MAX_LOG_SIZE // 8)):
            chunk = value[start:start + max(1, MAX_LOG_SIZE // 8)]
            self.handler.acquire()
            try:
                stream = self.handler.stream
                if stream is not None and stream.tell() + len(chunk.encode("utf-8")) > MAX_LOG_SIZE:
                    self.handler.doRollover()
                self.handler.handle(logging.LogRecord("desktop", logging.INFO, "", 0, chunk, (), None))
            finally:
                self.handler.release()
        return len(value)

    def flush(self) -> None:
        self.handler.flush()

    def close(self) -> None:
        if not self.closed:
            super().close()
            self.handler.close()


class LogOutput(Protocol):
    def write(self, value: str) -> int: ...
    def flush(self) -> None: ...


class Tee(io.TextIOBase):
    def __init__(self, log: LogOutput, console: TextIO | None) -> None:
        self.log, self.console = log, console
        self._lock = threading.Lock()

    def writable(self) -> bool:
        return True

    def write(self, value: str) -> int:
        with self._lock:
            self.log.write(value)
            self.log.flush()
            if self.console is not None:
                self.console.write(value)
                self.console.flush()
        return len(value)

    def flush(self) -> None:
        with self._lock:
            self.log.flush()
            if self.console is not None:
                self.console.flush()


def configure_desktop_logging(path: Path | None = None) -> Path:
    """Install one process-wide tee before the background runtime starts."""

    target = path or desktop_log_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > MAX_LOG_SIZE:
        target.replace(target.with_suffix(".log.1"))
    stream = RotatingLog(target)
    sys.stdout = Tee(stream, sys.stdout)
    sys.stderr = Tee(stream, sys.stderr)
    return target

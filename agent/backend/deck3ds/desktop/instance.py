"""Per-configuration single-instance lock and private UI hand-off."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
import secrets
from pathlib import Path
from typing import BinaryIO
from urllib.parse import parse_qs, urlparse

from platformdirs import user_cache_path


class InstanceLock:
    def __init__(self, key: str, directory: Path | None = None) -> None:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        root = directory or user_cache_path("3Decks", appauthor=False) / "runtime"
        self.directory = root
        self.lock_path = root / f"{digest}.lock"
        self.state_path = root / f"{digest}.json"
        self.stop_path = root / f"{digest}.stop"
        self._identity = ""
        self._stream: BinaryIO | None = None

    @classmethod
    def for_config(cls, path: Path | None) -> InstanceLock:
        key = str(path.resolve()) if path is not None else "default"
        return cls(key)

    def acquire(self) -> bool:
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            self.directory.chmod(0o700)
        except OSError:
            pass
        stream = self.lock_path.open("a+b")
        stream.seek(0)
        if stream.read(1) == b"":
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if sys.platform in {"win32", "cygwin"}:
                import msvcrt

                locking = getattr(msvcrt, "locking")
                locking(stream.fileno(), getattr(msvcrt, "LK_NBLCK"), 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            return False
        self._stream = stream
        self._identity = secrets.token_hex(16)
        try:
            self.publish_url("")
        except BaseException:
            self.release()
            raise
        return True

    def publish_url(self, url: str) -> None:
        if self._stream is None:
            raise RuntimeError("Instance lock is not held")
        payload = json.dumps({"pid": os.getpid(), "url": url, "instance": self._identity}).encode("utf-8")
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{self.state_path.name}.", dir=self.directory
        )
        try:
            with os.fdopen(descriptor, "wb") as output:
                # mkstemp creates mode 0600 on POSIX. Windows inherits the
                # user's application-directory ACL; fchmod is absent on 3.12.
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.state_path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    def existing_url(self) -> str:
        try:
            document = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ""
        url = document.get("url") if isinstance(document, dict) else ""
        if not isinstance(url, str):
            return ""
        try:
            parsed = urlparse(url)
            port = parsed.port
        except ValueError:
            return ""
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or port is None
            or not parse_qs(parsed.query).get("token")
        ):
            return ""
        return url

    def stop_requested(self) -> bool:
        """Only honor a request for this exact lifetime, never a stale PID."""
        try:
            return bool(self._identity) and self.stop_path.read_text(encoding="ascii") == self._identity
        except (OSError, UnicodeError):
            return False

    def request_stop(self, timeout: float = 30) -> bool:
        """Ask the native host to drain its resources, then wait for its lock.

        No HTTP shutdown endpoint or process-name matching is involved. A
        timeout aborts an installer instead of forcibly terminating a writer.
        """
        deadline = time.monotonic() + timeout
        while True:
            if self.acquire():
                self.release()
                return True
            try:
                state = json.loads(self.state_path.read_text(encoding="utf-8"))
                identity = state.get("instance") if isinstance(state, dict) else None
                if isinstance(identity, str) and len(identity) == 32:
                    descriptor, temporary = tempfile.mkstemp(prefix=".stop-", dir=self.directory)
                    try:
                        with os.fdopen(descriptor, "w", encoding="ascii") as output:
                            output.write(identity)
                        os.replace(temporary, self.stop_path)
                    finally:
                        Path(temporary).unlink(missing_ok=True)
            except (OSError, ValueError):
                pass
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)

    def release(self) -> None:
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            self.state_path.unlink(missing_ok=True)
            self.stop_path.unlink(missing_ok=True)
            if sys.platform in {"win32", "cygwin"}:
                import msvcrt

                stream.seek(0)
                locking = getattr(msvcrt, "locking")
                locking(stream.fileno(), getattr(msvcrt, "LK_UNLCK"), 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()

    def __enter__(self) -> InstanceLock:
        if not self.acquire():
            raise RuntimeError("3Decks is already running")
        return self

    def __exit__(self, *_error: object) -> None:
        self.release()

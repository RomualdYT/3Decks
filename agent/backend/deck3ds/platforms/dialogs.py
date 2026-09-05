"""Owned native dialog process; independent from persistent integration shells."""

from __future__ import annotations
import subprocess
import threading


class DialogProcess:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        self._closed = False

    def run(self, command: list[str], timeout: float = 120.0) -> str:
        with self._lock:
            if self._closed:
                raise RuntimeError("Agent is stopping")
            if self._process is not None:
                raise RuntimeError("A native dialog is already open")
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._process = process
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            if process.returncode:
                raise RuntimeError(
                    (stderr or stdout or "Native dialog failed").strip()[:160]
                )
            return stdout
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.communicate()
            raise RuntimeError("Native dialog timed out") from error
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None

    def close(self) -> None:
        with self._lock:
            self._closed = True
            process = self._process
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1.0)
            except OSError:
                pass

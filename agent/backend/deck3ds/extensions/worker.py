"""Bounded stdio RPC process. A timeout kills only the offending extension."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

from .manifest import ExtensionError, MAX_MESSAGE


class Worker:
    def __init__(self, package: Path, manifest: dict) -> None:
        self.package = package.resolve()
        self.manifest = manifest
        self.process: subprocess.Popen | None = None
        self.responses: queue.Queue = queue.Queue(maxsize=8)
        self.logs: deque[str] = deque(maxlen=40)
        self.lock = threading.Lock()
        self.sequence = 0

    def start(self, settings: dict, data_dir: Path) -> None:
        sdk_root = str(Path(__file__).resolve().parents[2])
        if self.manifest["runtime"] == "python":
            command = [
                sys.executable,
                "-u",
                "-B",
                "-c",
                "import runpy,sys; sys.path[:0]=sys.argv[1:3]; "
                "entry=sys.argv[3]; sys.argv=[entry]; runpy.run_path(entry,run_name='__main__')",
                sdk_root,
                str(self.package),
                str(self.package / self.manifest["entrypoint"]),
            ]
        else:
            command = list(self.manifest["command"])
        environment = dict(os.environ)
        # Stable SDK import, irrespective of where the user's package lives.
        environment["PYTHONPATH"] = sdk_root
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONUNBUFFERED"] = "1"
        try:
            self.process = subprocess.Popen(
                command,
                cwd=self.package,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as error:
            raise ExtensionError(
                "Runtime not found or extension could not start"
            ) from error
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        result = self.call(
            "initialize",
            {
                "api_version": 1,
                "extension_id": self.manifest["id"],
                "settings": settings,
                "data_dir": str(data_dir),
                "platform": sys.platform,
            },
        )
        if (
            not isinstance(result, dict)
            or type(result.get("api_version")) is not int
            or result["api_version"] != 1
        ):
            self.close()
            raise ExtensionError("Extension returned an incompatible API version")

    def _read_stdout(self) -> None:
        process = self.process
        try:
            while process and process.stdout:
                line = process.stdout.readline(MAX_MESSAGE + 1)
                if not line:
                    self.responses.put_nowait(
                        ExtensionError("Extension process exited")
                    )
                    return
                if len(line) > MAX_MESSAGE or not line.endswith(b"\n"):
                    raise ExtensionError("Extension response exceeded 64 KiB")
                value = json.loads(line)
                self.responses.put_nowait(value)
        except (ValueError, queue.Full, OSError, ExtensionError):
            if process and process.poll() is None:
                process.kill()
            try:
                self.responses.put_nowait(
                    ExtensionError("Invalid extension protocol output")
                )
            except queue.Full:
                pass

    def _read_stderr(self) -> None:
        process = self.process
        try:
            while process and process.stderr:
                line = process.stderr.readline(2048)
                if not line:
                    return
                self.logs.append(line.decode("utf-8", errors="replace").strip()[:500])
        except OSError:
            pass

    def call(self, method: str, params: dict, timeout: float = 5.0) -> object:
        if not self.lock.acquire(timeout=timeout):
            raise ExtensionError("Extension is busy; try again")
        try:
            process = self.process
            if process is None or process.poll() is not None:
                raise ExtensionError("Extension is not running")
            self.sequence += 1
            request_id = self.sequence
            encoded = (
                json.dumps(
                    {"id": request_id, "method": method, "params": params},
                    allow_nan=False,
                )
                + "\n"
            ).encode()
            if len(encoded) > MAX_MESSAGE:
                raise ExtensionError("Extension request exceeds 64 KiB")
            # Writing can block if a broken process stops reading stdin. Run it
            # in the same bounded I/O operation as the response wait.
            written: queue.Queue = queue.Queue(maxsize=1)

            def send() -> None:
                try:
                    process.stdin.write(encoded)
                    process.stdin.flush()
                    written.put(True)
                except (OSError, ValueError):
                    written.put(False)

            threading.Thread(target=send, daemon=True).start()
            deadline = time.monotonic() + timeout
            if not written.get(timeout=timeout):
                raise ExtensionError("Extension stopped accepting requests")
            response = self.responses.get(
                timeout=max(0.01, deadline - time.monotonic())
            )
            if isinstance(response, ExtensionError):
                raise response
            if (
                not isinstance(response, dict)
                or type(response.get("id")) is not int
                or response["id"] != request_id
            ):
                self.close()
                raise ExtensionError("Extension response id does not match the request")
            if response.get("error"):
                # Do not surface arbitrary tracebacks/settings from third-party code.
                raise ExtensionError(
                    "Extension handler failed; contact its author or run it in a terminal for diagnostics"
                )
            return response.get("result")
        except (queue.Empty, OSError, ValueError) as error:
            self.close()
            raise ExtensionError(
                "Extension timed out or disconnected (5 s limit)"
            ) from error
        finally:
            self.lock.release()

    def close(self) -> None:
        process, self.process = self.process, None
        if process is not None:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:
                    try:
                        stream.close()
                    except OSError:
                        pass

    def stop(self) -> None:
        """Best-effort cooperative shutdown; never depend on an untrusted hook."""
        try:
            if self.process and self.process.poll() is None:
                self.call("shutdown", {}, timeout=0.5)
        except ExtensionError:
            pass
        finally:
            self.close()

"""Public Python SDK for the language-neutral 3Decks stdio protocol v1.

Only this module is a stable author-facing Python API. Everything else in the
extensions package is host implementation detail.
"""

from __future__ import annotations

import contextlib
import json
import re
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class Context:
    settings: dict
    data_dir: Path
    platform: str
    extension_id: str

    def _file(self, name: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+\.json", name):
            raise ValueError("Storage filename must be a simple .json filename")
        return self.data_dir / name

    def load(self, name: str = "state.json", default=None):
        path = self._file(name)
        return (
            json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
        )

    def save(self, value: object, name: str = "state.json") -> None:
        path = self._file(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8"
        )
        temporary.replace(path)


@dataclass
class Result:
    ok: bool = True
    message: str = ""


@dataclass
class Snapshot:
    states: dict[str, bool] = field(default_factory=dict)
    dashboards: dict[str, dict] = field(default_factory=dict)
    sources: dict[str, list[dict]] = field(default_factory=dict)


class Extension:
    """Register action handlers and an optional snapshot provider, then serve."""

    def __init__(self) -> None:
        self._actions: dict[str, Callable] = {}
        self._poll: Callable = lambda context: Snapshot()
        self._initialize: Callable = lambda context: None
        self._shutdown: Callable = lambda context: None

    def action(self, action_id: str):
        def register(handler):
            if action_id in self._actions:
                raise ValueError(f"Duplicate handler: {action_id}")
            self._actions[action_id] = handler
            return handler

        return register

    def poll(self, handler):
        self._poll = handler
        return handler

    def initialize(self, handler):
        self._initialize = handler
        return handler

    def shutdown(self, handler):
        self._shutdown = handler
        return handler

    def serve(self) -> None:
        try:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
            sys.stdout.reconfigure(encoding="utf-8", errors="replace", newline="\n")
        except AttributeError:
            pass
        output = sys.stdout
        context = None
        with contextlib.redirect_stdout(sys.stderr):
            for line in iter(lambda: sys.stdin.readline(65537), ""):
                if len(line.encode("utf-8")) > 65536 or not line.endswith("\n"):
                    break
                request = {}
                try:
                    request = json.loads(line)
                    if not isinstance(request, dict):
                        request = {}
                        raise ValueError("Request must be an object")
                    method, params = request["method"], request.get("params", {})
                    if method == "initialize":
                        if params.get("api_version") != 1:
                            raise ValueError("Unsupported API version")
                        context = Context(
                            params["settings"],
                            Path(params["data_dir"]),
                            params["platform"],
                            params["extension_id"],
                        )
                        self._initialize(context)
                        result = {"api_version": 1}
                    elif context is None:
                        raise RuntimeError("initialize must be called first")
                    elif method == "action":
                        result = self._actions[params["action"]](
                            context, params.get("arguments", {})
                        )
                        if result is None:
                            result = Result()
                        if isinstance(result, Result):
                            result = {"ok": result.ok, "message": result.message}
                    elif method == "poll":
                        result = self._poll(context)
                        if isinstance(result, Snapshot):
                            result = {
                                "states": result.states,
                                "dashboards": result.dashboards,
                                "sources": result.sources,
                            }
                    elif method == "shutdown":
                        self._shutdown(context)
                        result = {}
                    else:
                        raise ValueError("Unknown method")
                    response = {"id": request["id"], "result": result}
                    encoded = (
                        json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n"
                    )
                    if len(encoded.encode("utf-8")) > 65536:
                        raise ValueError("Response exceeds 64 KiB")
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    encoded = (
                        json.dumps({"id": request.get("id"), "error": "handler_failed"})
                        + "\n"
                    )
                output.write(encoded)
                output.flush()
                if request.get("method") == "shutdown":
                    break

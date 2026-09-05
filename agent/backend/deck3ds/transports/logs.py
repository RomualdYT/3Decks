"""Journalisation : trace horodatée, bornée, relue par l'interface."""

from __future__ import annotations

from datetime import UTC, datetime
import math
from typing import Any


from .ports import AgentPort


class Logging:
    def __init__(self, context: AgentPort) -> None:
        self.context = context

    def _append_line(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        # Conservé avant l'affichage : l'interface montre les mêmes lignes que
        # la console, sans avoir à détourner la sortie standard.
        self.context._logs.append(f"[{stamp}] {message}")
        print(f"[{stamp}] {message}", flush=True)

    def log(self, message: str) -> None:
        self._append_line(message)
        self._record("agent.log", "info", message, {}, count=False)

    def _record(
        self,
        name: str,
        level: str,
        message: str,
        fields: dict[str, object],
        *,
        count: bool = True,
    ) -> None:
        safe_fields: dict[str, bool | float | int | str | None] = {}
        for key, value in list(fields.items())[:12]:
            if not isinstance(key, str) or not key:
                continue
            if value is None or isinstance(value, (bool, int)):
                safe_fields[key[:48]] = value
            elif isinstance(value, float) and math.isfinite(value):
                safe_fields[key[:48]] = value
            elif isinstance(value, str):
                safe_fields[key[:48]] = value[:256]
        event_name = name[:96]
        self.context._events.append(
            {
                "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace(
                    "+00:00", "Z"
                ),
                "name": event_name,
                "level": level if level in {"debug", "info", "warning", "error"} else "info",
                "message": message[:512],
                "fields": safe_fields,
            }
        )
        if count:
            self.context._counters[event_name] += 1

    def event(
        self, name: str, message: str = "", level: str = "info", **fields: object
    ) -> None:
        """Record a bounded structured event and its monotonic counter."""
        self._record(name, level, message, fields)
        if message:
            self._append_line(message)

    def debug(self, message: str) -> None:
        if self.context.verbose:
            self.context.log(message)

    def recent_logs(self) -> list[str]:
        """Dernières lignes journalisées, de la plus ancienne à la plus récente."""
        return list(self.context._logs)

    def recent_events(self) -> list[dict[str, Any]]:
        return list(self.context._events)

    def counters(self) -> dict[str, int]:
        return dict(sorted(self.context._counters.items()))

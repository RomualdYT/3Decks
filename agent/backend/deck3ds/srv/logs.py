"""Journalisation : trace horodatée, bornée, relue par l'interface."""

from __future__ import annotations

from datetime import datetime


class LoggingMixin:
    def log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        # Conservé avant l'affichage : l'interface montre les mêmes lignes que
        # la console, sans avoir à détourner la sortie standard.
        self._logs.append(f"[{stamp}] {message}")
        print(f"[{stamp}] {message}", flush=True)
    def debug(self, message: str) -> None:
        if self.verbose:
            self.log(message)
    def recent_logs(self) -> list[str]:
        """Dernières lignes journalisées, de la plus ancienne à la plus récente."""
        return list(self._logs)

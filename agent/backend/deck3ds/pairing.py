"""Appairage local d'une console Deck3DS.

Le secret de configuration active l'appairage et migre les anciennes consoles.
Le code court n'est qu'une autorisation temporaire, facile a recopier depuis
l'interface locale ; le service d'appareils émet ensuite un secret individuel.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import hmac
import secrets
import time
from collections import deque
from collections.abc import Callable
from enum import Enum
from typing import Any


PAIRING_CODE_TTL = 10 * 60
PAIRING_ATTEMPT_WINDOW = 60.0
PAIRING_ATTEMPTS_PER_SOURCE = 5
PAIRING_ATTEMPTS_GLOBAL = 30


class PairingResult(Enum):
    ACCEPTED = "accepted"
    INVALID = "invalid"
    RATE_LIMITED = "rate_limited"


class PairingManager:
    """Produit et valide un code decimal temporaire a six chiffres."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._code = ""
        self._expires_at = 0.0
        self._failures_by_source: dict[str, deque[float]] = {}
        self._global_failures: deque[float] = deque()
        self.rotate()

    def rotate(self) -> str:
        """Remplace immédiatement le code et retourne la nouvelle valeur."""
        self._code = f"{secrets.randbelow(1_000_000):06d}"
        self._expires_at = self._clock() + PAIRING_CODE_TTL
        # Un code neuf ouvre une nouvelle fenêtre d'appairage explicite. Les
        # échecs de l'ancien code ne doivent pas bloquer l'utilisateur légitime.
        self._failures_by_source.clear()
        self._global_failures.clear()
        return self._code

    def _ensure_fresh(self) -> None:
        if self._clock() >= self._expires_at:
            self.rotate()

    @staticmethod
    def _discard_old(attempts: deque[float], now: float) -> None:
        cutoff = now - PAIRING_ATTEMPT_WINDOW
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

    def consume_result(
        self, candidate: object, source: str = "unknown"
    ) -> PairingResult:
        """Validate a one-time code and retain the refusal reason for metrics."""
        self._ensure_fresh()
        now = self._clock()
        source_key = source or "unknown"
        source_failures = self._failures_by_source.setdefault(source_key, deque())
        self._discard_old(source_failures, now)
        self._discard_old(self._global_failures, now)

        if (
            len(source_failures) >= PAIRING_ATTEMPTS_PER_SOURCE
            or len(self._global_failures) >= PAIRING_ATTEMPTS_GLOBAL
        ):
            return PairingResult.RATE_LIMITED

        # Le format exact évite que différentes représentations d'un même code
        # élargissent inutilement l'espace d'entrée accepté.
        valid = (
            isinstance(candidate, str)
            and len(candidate) == 6
            and candidate.isascii()
            and candidate.isdigit()
            and hmac.compare_digest(candidate, self._code)
        )
        if valid:
            self.rotate()
            return PairingResult.ACCEPTED
        else:
            source_failures.append(now)
            self._global_failures.append(now)
            return PairingResult.INVALID

    def consume(self, candidate: object, source: str = "unknown") -> bool:
        """Compatibility boolean API used by callers that need no reason."""
        return self.consume_result(candidate, source) is PairingResult.ACCEPTED

    def snapshot(self, required: bool) -> dict[str, Any]:
        """État destiné exclusivement à l'interface web locale."""
        self._ensure_fresh()
        remaining = max(0, int(self._expires_at - self._clock()))
        return {
            "required": required,
            "code": self._code if required else "",
            "expires_in": remaining if required else 0,
        }

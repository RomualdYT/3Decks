"""Appairage local d'une console Deck3DS.

Le jeton long reste le secret durable stocke dans la configuration. Le code
court n'est qu'une autorisation temporaire, facile a recopier depuis
l'interface locale de l'agent lors de la premiere connexion d'une console.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import hmac
import secrets
import time
from typing import Any


PAIRING_CODE_TTL = 10 * 60


class PairingManager:
    """Produit et valide un code decimal temporaire a six chiffres."""

    def __init__(self) -> None:
        self._code = ""
        self._expires_at = 0.0
        self.rotate()

    def rotate(self) -> str:
        """Remplace immédiatement le code et retourne la nouvelle valeur."""
        self._code = f"{secrets.randbelow(1_000_000):06d}"
        self._expires_at = time.monotonic() + PAIRING_CODE_TTL
        return self._code

    def _ensure_fresh(self) -> None:
        if time.monotonic() >= self._expires_at:
            self.rotate()

    def consume(self, candidate: object) -> bool:
        """Valide puis invalide un code afin d'empêcher sa réutilisation."""
        self._ensure_fresh()
        if not isinstance(candidate, str):
            return False
        valid = hmac.compare_digest(candidate.strip(), self._code)
        if valid:
            self.rotate()
        return valid

    def snapshot(self, required: bool) -> dict[str, Any]:
        """État destiné exclusivement à l'interface web locale."""
        self._ensure_fresh()
        remaining = max(0, int(self._expires_at - time.monotonic()))
        return {
            "required": required,
            "code": self._code if required else "",
            "expires_in": remaining if required else 0,
        }

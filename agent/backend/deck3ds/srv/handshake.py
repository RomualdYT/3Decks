"""Accueil d'une console : version, jeton, état initial."""

from __future__ import annotations

import asyncio
import platform as platform_module
from typing import Any
from .. import protocol
from .. import messages
from .parts import Client, VERSION


class HandshakeMixin:
    async def _accept_handshake(self, client: Client, message: dict[str, Any]) -> bool:
        """Vérifie la version du protocole et le jeton.

        Retourne `False` si la console a été refusée ; la réponse est alors déjà
        émise et la connexion fermée.
        """
        version = message.get("protocol")
        if version != protocol.PROTOCOL_VERSION:
            await self._reject_handshake(
                client,
                f"protocole {version}, attendu {protocol.PROTOCOL_VERSION}",
                "version de protocole incompatible",
            )
            return False

        # Comparaison simple : le jeton protège d'un usage accidentel sur le
        # réseau local, il ne prétend pas résister à une analyse temporelle.
        if self.config.token and message.get("token") != self.config.token:
            await self._reject_handshake(client, "jeton invalide", "jeton refuse")
            return False

        return True
    async def _reject_handshake(self, client: Client, reason: str, note: str) -> None:
        """Refuse une console et ferme la connexion."""
        await client.send(protocol.hello_error(reason))
        self.log(f"Console #{client.id}: {note}")
        await client.close()
    async def _send_initial_state(self, client: Client) -> None:
        """Met la console à niveau juste après son acceptation.

        Une console qui vient d'arriver ne possède aucune pochette : celle en
        cours lui est transmise même si elle n'a pas changé.
        """
        if self._last_payload is None:
            # Première console connectée : une collecte immédiate évite de
            # laisser le tableau de bord vide.
            self._wake().set()
            return

        await client.send(self._last_payload)
        art = self._artwork.payload()
        if art is not None:
            await client.send_raw(art)
    async def _handle_hello(self, client: Client, message: dict[str, Any]) -> None:
        if not await self._accept_handshake(client, message):
            return

        # La configuration est localisée pour cette console. Le catalogue de
        # messages historique reste synchronisé pour les retours d'action.
        requested_language = str(message.get("language", "en"))
        client.language = requested_language if requested_language in ("en", "fr") else "en"
        messages.set_language(client.language)
        client.authenticated = True

        # Première console : les pages dynamiques ne sont pas encore remplies.
        # Les alimenter avant d'envoyer la configuration évite une page vide.
        if self._has_dynamic_pages() and not self._published_windows:
            windows = await asyncio.to_thread(self.platform.list_windows)
            active = await asyncio.to_thread(self.platform.get_active_app)
            self._fill_dynamic_pages(windows, active)

        await client.send(
            protocol.hello_ok(
                VERSION, platform_module.node() or "PC", self.platform.name
            )
        )
        await client.send(self._config_message(client.language))
        await self._send_initial_state(client)

        self.log(f"Console #{client.id}: handshake accepte")

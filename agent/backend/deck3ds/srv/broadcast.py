"""Diffusion aux consoles connectées, éviction des injoignables."""

from __future__ import annotations

from typing import Any
from .parts import Client
from ..extensions.bridge import localized_state


class BroadcastMixin:
    def _audience(self) -> list[Client]:
        """Consoles autorisées à recevoir un message.

        La liste est copiée : une console peut être retirée pendant l'envoi,
        ce qui invaliderait un parcours direct de l'ensemble.
        """
        return [client for client in list(self.clients) if client.authenticated]
    async def _broadcast(self, message: dict[str, Any]) -> None:
        """Envoie un message à toutes les consoles authentifiées.

        Une console injoignable est retirée : sans cela, chaque cycle
        réessaierait indéfiniment d'écrire dans une socket fermée.
        """
        for client in self._audience():
            if not await client.send(message):
                await self._drop(client)
    async def _drop(self, client: Client) -> None:
        """Retire une console dont la connexion est perdue."""
        self.clients.discard(client)
        await client.close()
    async def _publish(self, delta: dict[str, Any], art: bytes | None) -> None:
        """Transmet le différentiel, puis la pochette si elle a changé."""
        # Un différentiel réduit au seul type n'annonce aucun changement.
        has_change = len(delta) > 1
        if not has_change and art is None:
            return

        for client in self._audience():
            if has_change and not await client.send(localized_state(delta, getattr(client, "language", "en"))):
                await self._drop(client)
                continue
            if art is not None:
                await client.send_raw(art)

"""Cycle de vie d'une connexion et routage des messages."""

from __future__ import annotations

import asyncio
from typing import Any
from .. import protocol
from ..extensions.bridge import localized_state
from .parts import Client


class ConnectionMixin:
    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        client = Client(reader, writer)
        self.clients.add(client)
        self.log(f"Console #{client.id} connectee depuis {client.address}")

        try:
            await self._read_messages(client, reader)
        except (ConnectionError, OSError):
            pass
        finally:
            self.clients.discard(client)
            await client.close()
            self.log(f"Console #{client.id} deconnectee")
    async def _read_messages(
        self, client: Client, reader: asyncio.StreamReader
    ) -> None:
        """Lit le flux d'une console jusqu'à sa fermeture."""
        while True:
            data = await reader.read(8192)
            if not data:
                return

            client.reader_state.feed(data)
            if not await self._dispatch_available(client):
                return
    async def _dispatch_available(self, client: Client) -> bool:
        """Traite les messages complets déjà reçus.

        Retourne `False` si une trame invalide impose de couper la connexion :
        le flux est alors désynchronisé et rien ne permet de s'y resynchroniser.
        """
        try:
            for message in client.reader_state:
                await self._handle_message(client, message)
        except protocol.ProtocolError as error:
            self.log(f"Console #{client.id}: trame invalide ({error})")
            return False
        return True
    async def _handle_message(self, client: Client, message: dict[str, Any]) -> None:
        kind = message.get("type")

        if kind == "hello":
            await self._handle_hello(client, message)
            return

        # Tout le reste exige un handshake réussi.
        if not client.authenticated:
            self.debug(f"Console #{client.id}: message avant handshake ({kind})")
            return

        # Table de routage plutôt qu'une chaîne de comparaisons : ajouter un
        # message se voit d'un coup d'œil, et un type inconnu ne peut pas être
        # confondu avec un oubli de branche.
        handlers = {
            "button.press": self._handle_button,
            "value.set": self._handle_value,
            "config.request": self._handle_config_request,
            "ping": self._handle_ping,
        }
        handler = handlers.get(kind)
        if handler is None:
            self.debug(f"Console #{client.id}: type ignore ({kind})")
            return
        await handler(client, message)
    async def _handle_ping(self, client: Client, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        await client.send(
            protocol.pong(request_id if isinstance(request_id, int) else 0)
        )
    async def _handle_config_request(
        self, client: Client, message: dict[str, Any]
    ) -> None:
        """Renvoie la mise en page, puis l'état courant s'il existe."""
        await client.send(self._config_message(client.language))
        if self._last_payload is not None:
            await client.send(localized_state(self._last_payload, client.language))

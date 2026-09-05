"""Cycle de vie d'une connexion et routage des messages."""

from __future__ import annotations

import asyncio
from typing import Any
from .. import protocol
from ..extensions.bridge import localized_state
from .limits import HANDSHAKE_TIMEOUT, MAX_PENDING_CONNECTIONS
from .parts import Client


from .ports import AgentPort


class Connection:
    def __init__(self, context: AgentPort) -> None:
        self.context = context

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self.context._client_tasks.add(task)
        client = Client(reader, writer)

        pending = sum(not item.authenticated for item in self.context.clients)
        if pending >= MAX_PENDING_CONNECTIONS:
            self.context.event(
                "tcp.connection.refused",
                f"Connexion refusee depuis {client.address}: trop de handshakes en attente",
                level="warning",
                reason="pending_limit",
                address=client.address,
            )
            try:
                await client.send(
                    protocol.hello_error("serveur occupe", code="server_busy")
                )
            finally:
                if task is not None:
                    self.context._client_tasks.discard(task)
                await client.close()
            return

        self.context.clients.add(client)
        self.context.event(
            "tcp.connection.opened",
            f"Console #{client.id} connectee depuis {client.address}",
            client_id=client.id,
            address=client.address,
        )

        try:
            await self.context._read_messages(client, reader)
        except TimeoutError:
            self.context.event(
                "tcp.handshake.timeout",
                f"Console #{client.id}: handshake expire",
                level="warning",
                client_id=client.id,
            )
        except (ConnectionError, OSError):
            pass
        finally:
            if task is not None:
                self.context._client_tasks.discard(task)
            self.context.clients.discard(client)
            await client.close()
            self.context.event(
                "tcp.connection.closed",
                f"Console #{client.id} deconnectee",
                client_id=client.id,
                authenticated=client.authenticated,
            )

    async def _read_messages(
        self, client: Client, reader: asyncio.StreamReader
    ) -> None:
        """Lit le flux, avec une échéance absolue avant authentification."""
        loop = asyncio.get_running_loop()
        handshake_deadline = loop.time() + HANDSHAKE_TIMEOUT
        while True:
            if client.authenticated:
                data = await reader.read(8192)
            else:
                remaining = handshake_deadline - loop.time()
                if remaining <= 0:
                    raise TimeoutError
                data = await asyncio.wait_for(reader.read(8192), timeout=remaining)
            if not data:
                return

            client.reader_state.feed(data)
            if not await self.context._dispatch_available(client):
                return

    async def _dispatch_available(self, client: Client) -> bool:
        """Traite les messages complets déjà reçus.

        Retourne `False` si une trame invalide impose de couper la connexion :
        le flux est alors désynchronisé et rien ne permet de s'y resynchroniser.
        """
        try:
            for message in client.reader_state:
                await self.context._handle_message(client, message)
        except protocol.ProtocolError as error:
            self.context.event(
                "tcp.frame.invalid",
                f"Console #{client.id}: trame invalide ({error})",
                level="warning",
                client_id=client.id,
            )
            return False
        return True

    async def _handle_message(self, client: Client, message: dict[str, Any]) -> None:
        kind = message.get("type")

        if kind == "hello":
            await self.context._handle_hello(client, message)
            return

        # Tout le reste exige un handshake réussi.
        if not client.authenticated:
            self.context.debug(
                f"Console #{client.id}: message avant handshake ({kind})"
            )
            return

        # Table de routage plutôt qu'une chaîne de comparaisons : ajouter un
        # message se voit d'un coup d'œil, et un type inconnu ne peut pas être
        # confondu avec un oubli de branche.
        handlers = {
            "button.press": self.context._handle_button,
            "value.set": self.context._handle_value,
            "config.request": self.context._handle_config_request,
            "ping": self.context._handle_ping,
        }
        handler = handlers.get(kind)
        if handler is None:
            self.context.debug(f"Console #{client.id}: type ignore ({kind})")
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
        await client.send(self.context._config_message(client.language))
        if self.context._last_payload is not None:
            await client.send(
                localized_state(self.context._last_payload, client.language)
            )

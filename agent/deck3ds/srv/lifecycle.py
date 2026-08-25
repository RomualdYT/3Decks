"""Démarrage et arrêt du serveur, interface de configuration incluse."""

from __future__ import annotations

import asyncio
import socket
from .parts import VERSION


class LifecycleMixin:
    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client,
            self.config.host,
            self.config.port,
            reuse_address=True,
        )

        addresses = ", ".join(
            f"{sock.getsockname()[0]}:{sock.getsockname()[1]}"
            for sock in self._server.sockets
        )
        self.log(f"Agent Deck3DS {VERSION} en ecoute sur {addresses}")

        for hint in self.local_addresses():
            self.log(f"  adresse a saisir sur la 3DS : {hint}")

        if not self.config.token:
            self.log("  aucun jeton configure : toute console du reseau peut agir")

        await self._start_ui()

        poller = asyncio.create_task(self._poll_loop())

        try:
            async with self._server:
                await self._server.serve_forever()
        except asyncio.CancelledError:
            pass
        finally:
            poller.cancel()
            for client in list(self.clients):
                await client.close()
            if self._ui is not None:
                await self._ui.close()
    async def _start_ui(self) -> None:
        """Démarre l'interface de configuration, si elle est demandée.

        Un échec n'interrompt pas l'agent : un port déjà pris ne doit pas priver
        la console de sa surface de contrôle, qui reste la fonction première.
        """
        if self.ui_port is None:
            return

        # Import différé : l'agent démarre sans l'interface si elle n'est pas
        # utilisée, et le module d'interface peut importer le serveur.
        from .ui.api import Api
        from .ui.http import UiServer

        api = Api(self)
        ui = UiServer(api.routes(), port=self.ui_port, log=self.log)

        try:
            await ui.start()
        except OSError as error:
            self.log(f"Interface indisponible sur le port {self.ui_port} : {error}")
            return

        self._ui = ui

        if self.on_ui_ready is not None:
            try:
                self.on_ui_ready(ui.url)
            except Exception as error:  # ouvrir le navigateur reste accessoire
                self.debug(f"ouverture du navigateur impossible : {error}")
    def local_addresses(self) -> list[str]:
        """Devine les adresses utilisables, pour éviter à l'utilisateur de
        chercher son IP à la main."""
        found: list[str] = []
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Aucune donnée n'est envoyée : cela sert seulement à déterminer
            # l'interface qu'emprunterait une connexion sortante.
            probe.connect(("8.8.8.8", 80))
            found.append(f"{probe.getsockname()[0]}:{self.config.port}")
            probe.close()
        except OSError:
            pass
        return found
    async def _poll_loop(self) -> None:
        try:
            await self._poll_forever()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            # Sans cette trace, une panne de la boucle passait inaperçue : la
            # tâche mourait, plus rien ne se rafraîchissait, et l'agent semblait
            # fonctionner puisqu'il répondait toujours aux appuis. Un tel silence
            # coûte des heures de diagnostic.
            self.log(
                f"Collecte interrompue : {type(error).__name__}: {error}. "
                "L'etat ne sera plus rafraichi, redemarrez l'agent."
            )
            raise

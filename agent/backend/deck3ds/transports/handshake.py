"""Accueil d'une console : version, jeton, état initial."""

from __future__ import annotations

import hmac
import platform as platform_module
from typing import Any
from .. import protocol
from .parts import Client, VERSION
from .limits import MAX_AUTHENTICATED_CLIENTS
from ..extensions.bridge import fill_sources, localized_state
from ..pairing import PairingResult
from ..services.devices import DeviceStoreError


from .ports import AgentPort


class Handshake:
    def __init__(self, context: AgentPort) -> None:
        self.context = context

    async def _accept_handshake(self, client: Client, message: dict[str, Any]) -> bool:
        """Vérifie la version du protocole et le jeton.

        Retourne `False` si la console a été refusée ; la réponse est alors déjà
        émise et la connexion fermée.
        """
        version = message.get("protocol")
        if version != protocol.PROTOCOL_VERSION:
            await self.context._reject_handshake(
                client,
                f"protocole {version}, attendu {protocol.PROTOCOL_VERSION}",
                "version de protocole incompatible",
            )
            return False

        authenticated = sum(item.authenticated for item in self.context.clients)
        if authenticated >= MAX_AUTHENTICATED_CLIENTS:
            await self.context._reject_handshake(
                client,
                "serveur occupe",
                "limite de consoles authentifiees atteinte",
                code="server_busy",
            )
            return False

        if self.context.config.token:
            supplied = message.get("token")
            name = message.get("device")
            try:
                device = await self.context.services.devices.authenticate(supplied, name)
                if device is not None:
                    client.device_id = device["id"]
                    client.device_name = device["name"]
                elif isinstance(supplied, str) and hmac.compare_digest(
                    supplied, self.context.config.token
                ):
                    # Migration sans rupture : une console qui possédait le
                    # jeton historique reçoit immédiatement son propre secret.
                    client.issued_token, device = (
                        await self.context.services.devices.issue(name)
                    )
                    client.device_id = device["id"]
                    client.device_name = device["name"]
                    client.paired_now = True
                else:
                    pairing_result = self.context.pairing.consume_result(
                        message.get("pair_code"),
                        getattr(client, "peer_host", "unknown"),
                    )
                    if pairing_result is not PairingResult.ACCEPTED:
                        await self.context._reject_handshake(
                            client,
                            "trop de tentatives d'appairage"
                            if pairing_result is PairingResult.RATE_LIMITED
                            else "jeton invalide, appairage requis",
                            "appairage temporairement limite"
                            if pairing_result is PairingResult.RATE_LIMITED
                            else "appairage requis",
                            code="pairing_rate_limited"
                            if pairing_result is PairingResult.RATE_LIMITED
                            else "pairing_required",
                        )
                        return False
                    # Le code à usage unique ne révèle plus le jeton maître :
                    # il crée une identité révocable propre à cette console.
                    client.issued_token, device = (
                        await self.context.services.devices.issue(name)
                    )
                    client.device_id = device["id"]
                    client.device_name = device["name"]
                    client.paired_now = True
            except DeviceStoreError:
                await self.context._reject_handshake(
                    client,
                    "identite de console indisponible",
                    "registre de consoles indisponible",
                    code="credential_store_error",
                )
                return False

        return True

    async def _reject_handshake(
        self,
        client: Client,
        reason: str,
        note: str,
        code: str = "",
    ) -> None:
        """Refuse une console et ferme la connexion."""
        await client.send(protocol.hello_error(reason, code=code))
        self.context.event(
            "tcp.handshake.refused",
            f"Console #{client.id}: {note}",
            level="warning",
            client_id=client.id,
            code=code or "refused",
        )
        await client.close()

    async def _send_initial_state(self, client: Client) -> None:
        """Met la console à niveau juste après son acceptation.

        Une console qui vient d'arriver ne possède aucune pochette : celle en
        cours lui est transmise même si elle n'a pas changé.
        """
        if self.context._last_payload is None:
            # Première console connectée : une collecte immédiate évite de
            # laisser le tableau de bord vide.
            self.context._wake().set()
            return

        await client.send(
            localized_state(
                self.context._last_payload, getattr(client, "language", "en")
            )
        )
        art = self.context._artwork.payload()
        if art is not None:
            await client.send_raw(art)

    async def _handle_hello(self, client: Client, message: dict[str, Any]) -> None:
        if client.authenticated:
            # Empêche toute trame collée après ce second hello d'être traitée
            # comme une commande authentifiée pendant la fermeture.
            client.authenticated = False
            await self.context._reject_handshake(
                client,
                "handshake deja effectue",
                "second handshake refuse",
            )
            return
        if not await self.context._accept_handshake(client, message):
            return

        # La configuration et les retours d'action sont localisés pour cette
        # console, sans modifier un état global partagé avec les autres.
        requested_language = str(message.get("language", "en"))
        client.language = (
            requested_language if requested_language in ("en", "fr") else "en"
        )
        client.authenticated = True
        fill_sources(self.context.extensions, self.context.config)

        # Première console : les pages dynamiques ne sont pas encore remplies.
        # Les alimenter avant d'envoyer la configuration évite une page vide.
        if self.context._has_dynamic_pages() and not self.context._published_windows:
            windows = await self.context.native_pool.run(
                self.context.platform.list_windows
            )
            active = await self.context.native_pool.run(
                self.context.platform.get_active_app
            )
            self.context._fill_dynamic_pages(windows, active)

        await client.send(
            protocol.hello_ok(
                VERSION,
                getattr(self.context, "_discovery_name", None)
                or platform_module.node()
                or "PC",
                self.context.platform.name,
                client.issued_token,
            )
        )
        await client.send(self.context._config_message(client.language))
        await self.context._send_initial_state(client)

        suffix = " apres appairage" if client.paired_now else ""
        self.context.event(
            "tcp.handshake.accepted",
            f"Console #{client.id}: handshake accepte{suffix}",
            client_id=client.id,
            device_id=client.device_id,
            paired=client.paired_now,
        )

"""Découverte de l'agent par les consoles présentes sur le réseau local."""

from __future__ import annotations

import asyncio
import json
import platform as platform_module
import socket
import subprocess
import sys
import time
from typing import Any, cast

from .. import protocol
from .parts import VERSION
from .ports import AgentPort


DISCOVERY_PORT = 38122
DISCOVERY_REQUEST = "deck3ds.discover"
DISCOVERY_RESPONSE = "deck3ds.agent"
DISCOVERY_MULTICAST = "239.255.77.83"
MAX_DATAGRAM = 512


def _friendly_device_name() -> str:
    """Retourne le nom choisi par l'utilisateur plutôt qu'un hostname brut."""
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["/usr/sbin/scutil", "--get", "ComputerName"],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            name = result.stdout.strip()
            if result.returncode == 0 and name:
                return name
        except (OSError, subprocess.SubprocessError):
            pass
    return platform_module.node() or "3Decks Agent"


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, owner: Any) -> None:
        self.owner = owner
        self.transport: asyncio.DatagramTransport | None = None
        self._last_log: dict[str, float] = {}

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data: bytes, address: tuple[str, int]) -> None:
        if self.transport is None or not data or len(data) > MAX_DATAGRAM:
            return
        try:
            request = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(request, dict):
            return
        if request.get("type") != DISCOVERY_REQUEST:
            return
        if request.get("protocol") != protocol.PROTOCOL_VERSION:
            return

        now = time.monotonic()
        if now - self._last_log.get(address[0], 0.0) >= 8.0:
            self.owner.log(f"Recherche automatique recue de {address[0]}")
            self._last_log[address[0]] = now

        payload = self.owner.discovery_payload()
        nonce = request.get("nonce")
        if isinstance(nonce, int) and not isinstance(nonce, bool):
            payload["nonce"] = nonce
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        if len(encoded) <= MAX_DATAGRAM:
            self.transport.sendto(encoded, address)

    def error_received(self, error: Exception) -> None:
        self.owner.debug(f"decouverte locale: {error}")


class Discovery:
    def __init__(self, context: AgentPort) -> None:
        self.context = context

    """Ajoute au serveur une annonce UDP légère et sans état de session."""

    def discovery_payload(self) -> dict[str, Any]:
        return {
            "type": DISCOVERY_RESPONSE,
            "protocol": protocol.PROTOCOL_VERSION,
            "name": getattr(self.context, "_discovery_name", None)
            or _friendly_device_name(),
            "platform": self.context.platform.name,
            "port": self.context.config.port,
            "version": VERSION,
            "pairing_required": bool(self.context.config.token),
        }

    async def _start_discovery(self) -> None:
        loop = asyncio.get_running_loop()
        self.context._discovery_name = await self.context.native_pool.run(
            _friendly_device_name
        )

        # Un multicast local complète les diffusions IPv4, souvent filtrées par
        # les points d'accès Wi-Fi. Le même socket continue d'accepter les
        # annonces limitées et dirigées historiques.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("0.0.0.0", DISCOVERY_PORT))
            membership = socket.inet_aton(DISCOVERY_MULTICAST) + socket.inet_aton(
                "0.0.0.0"
            )
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            except OSError as error:
                self.context.debug(f"multicast de decouverte indisponible : {error}")
            sock.setblocking(False)
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _DiscoveryProtocol(self.context),
                sock=sock,
            )
        except OSError as error:
            sock.close()
            self.context.log(
                f"Decouverte automatique indisponible sur le port "
                f"{DISCOVERY_PORT} : {error}"
            )
            return
        self.context._discovery_transport = transport
        self.context.log(f"Decouverte automatique active sur UDP {DISCOVERY_PORT}")

    def _stop_discovery(self) -> None:
        transport = self.context._discovery_transport
        self.context._discovery_transport = None
        if transport is not None:
            transport.close()

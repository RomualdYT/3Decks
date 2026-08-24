"""Encodage et décodage des trames Deck3DS.

Le protocole est décrit dans `docs/PROTOCOL.md`. Chaque message est un objet
JSON précédé de sa longueur sur quatre octets en big-endian.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import json
import struct
from typing import Any

PROTOCOL_VERSION = 1

#: Taille maximale d'un message. Doit rester alignée sur NET_MAX_MESSAGE côté 3DS.
MAX_MESSAGE = 65536

_HEADER = struct.Struct(">I")
HEADER_SIZE = _HEADER.size


class ProtocolError(Exception):
    """Trame invalide ou trop grande."""


def encode_raw(payload: bytes) -> bytes:
    """Ajoute l'en-tête de longueur à une charge utile déjà sérialisée.

    Utilisé pour les trames binaires, comme les pochettes d'album, qui ne sont
    pas du JSON.
    """
    if len(payload) > MAX_MESSAGE:
        raise ProtocolError(
            f"charge de {len(payload)} octets, maximum {MAX_MESSAGE}"
        )
    return _HEADER.pack(len(payload)) + payload


def encode(message: dict[str, Any]) -> bytes:
    """Sérialise un message et ajoute son en-tête de longueur."""
    # `separators` évite les espaces inutiles : les messages d'état sont
    # envoyés plusieurs fois par seconde.
    payload = json.dumps(
        message, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")

    if len(payload) > MAX_MESSAGE:
        raise ProtocolError(f"message de {len(payload)} octets, maximum {MAX_MESSAGE}")

    return _HEADER.pack(len(payload)) + payload


class FrameReader:
    """Accumule des octets et en extrait les messages complets.

    TCP ne préserve pas les frontières de messages : un `recv` peut renvoyer
    un demi-message ou trois messages collés. Cette classe gère les deux cas.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> None:
        """Ajoute des octets reçus du réseau."""
        self._buffer.extend(data)

    def __iter__(self):
        """Produit les messages complets disponibles."""
        while True:
            if len(self._buffer) < HEADER_SIZE:
                return

            (length,) = _HEADER.unpack_from(self._buffer, 0)

            if length > MAX_MESSAGE:
                # Un pair qui annonce une taille aberrante ne suit pas le
                # protocole : inutile d'attendre les octets promis.
                raise ProtocolError(f"longueur annoncee invalide: {length}")

            total = HEADER_SIZE + length
            if len(self._buffer) < total:
                return

            payload = bytes(self._buffer[HEADER_SIZE:total])
            del self._buffer[:total]

            try:
                decoded = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ProtocolError(f"JSON illisible: {error}") from error

            if not isinstance(decoded, dict):
                raise ProtocolError("le message racine doit etre un objet")

            yield decoded


# --- Constructeurs de messages sortants ---------------------------------------


def hello_ok(agent_version: str, host: str, platform: str) -> dict[str, Any]:
    return {
        "type": "hello.ok",
        "protocol": PROTOCOL_VERSION,
        "agent": agent_version,
        "host": host,
        "platform": platform,
    }


def hello_error(reason: str) -> dict[str, Any]:
    return {"type": "hello.error", "reason": reason}


def action_result(
    request_id: int,
    ok: bool,
    message: str = "",
    open_page: str | None = None,
    open_settings: bool = False,
    open_modal: bool = False,
    toggle_frame: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "action.result",
        "id": request_id,
        "ok": ok,
    }
    if message:
        result["message"] = message
    if open_page:
        result["open_page"] = open_page
    if open_settings:
        result["open_settings"] = True
    if open_modal:
        result["open_modal"] = True
    if toggle_frame:
        result["toggle_frame"] = True
    return result


def pong(request_id: int) -> dict[str, Any]:
    return {"type": "pong", "id": request_id}

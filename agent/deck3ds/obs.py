"""Client minimal pour le protocole obs-websocket 5.x.

OBS 28 et suivants embarquent un serveur WebSocket. Deck3DS n'ayant aucune
dependance externe, ce module implemente uniquement la petite partie de RFC 6455
necessaire pour envoyer les requetes JSON utilisees par les boutons.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import uuid
from dataclasses import dataclass
from typing import Any

from .config import ObsConfig


_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_MAX_MESSAGE = 2 * 1024 * 1024


class ObsError(Exception):
    """Connexion ou requete OBS impossible."""


@dataclass
class ObsStatus:
    obs_version: str = ""
    websocket_version: str = ""
    scenes: list[str] | None = None
    current_scene: str = ""

    def as_payload(self) -> dict[str, Any]:
        return {
            "connected": True,
            "obs_version": self.obs_version,
            "websocket_version": self.websocket_version,
            "scenes": list(self.scenes or []),
            "current_scene": self.current_scene,
        }


class ObsClient:
    """Connexion courte a OBS, ouverte pour une action puis refermee."""

    def __init__(self, config: ObsConfig) -> None:
        self.config = config
        self._socket: socket.socket | None = None
        self._buffer = bytearray()

    def __enter__(self) -> ObsClient:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    # --- Connexion et identification -----------------------------------------

    def connect(self) -> None:
        if self._socket is not None:
            return

        try:
            sock = socket.create_connection(
                (self.config.host, self.config.port), timeout=self.config.timeout
            )
            sock.settimeout(self.config.timeout)
        except OSError as error:
            raise ObsError(
                f"OBS injoignable sur {self.config.host}:{self.config.port} : {error}"
            ) from error

        self._socket = sock

        try:
            self._handshake()
            hello = self._receive_json()
            if hello.get("op") != 0:
                raise ObsError("OBS n'a pas envoye le message d'accueil attendu")

            data = hello.get("d")
            if not isinstance(data, dict):
                raise ObsError("message d'accueil OBS invalide")

            rpc_version = data.get("rpcVersion", 1)
            identify: dict[str, Any] = {
                "rpcVersion": rpc_version if isinstance(rpc_version, int) else 1,
                # Aucun evenement n'est necessaire pour des boutons ponctuels.
                "eventSubscriptions": 0,
            }

            authentication = data.get("authentication")
            if isinstance(authentication, dict):
                if not self.config.password:
                    raise ObsError("OBS demande un mot de passe WebSocket")
                challenge = authentication.get("challenge")
                salt = authentication.get("salt")
                if not isinstance(challenge, str) or not isinstance(salt, str):
                    raise ObsError("defi d'authentification OBS invalide")
                identify["authentication"] = self._authentication(challenge, salt)

            self._send_json({"op": 1, "d": identify})
            identified = self._receive_json()
            if identified.get("op") != 2:
                raise ObsError("OBS a refuse l'identification WebSocket")
        except Exception:
            self.close()
            raise

    def _handshake(self) -> None:
        assert self._socket is not None
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        host = self.config.host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"

        request = (
            "GET / HTTP/1.1\r\n"
            f"Host: {host}:{self.config.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "Sec-WebSocket-Protocol: obswebsocket.json\r\n"
            "\r\n"
        ).encode("ascii")
        self._socket.sendall(request)

        while b"\r\n\r\n" not in self._buffer:
            if len(self._buffer) > 32 * 1024:
                raise ObsError("reponse HTTP OBS trop grande")
            chunk = self._socket.recv(4096)
            if not chunk:
                raise ObsError("OBS a ferme la connexion pendant l'ouverture")
            self._buffer.extend(chunk)

        head, _, rest = bytes(self._buffer).partition(b"\r\n\r\n")
        self._buffer = bytearray(rest)
        lines = head.decode("latin-1").split("\r\n")

        if not lines or " 101 " not in f" {lines[0]} ":
            status = lines[0] if lines else "reponse vide"
            raise ObsError(f"OBS a refuse WebSocket ({status})")

        headers: dict[str, str] = {}
        for line in lines[1:]:
            name, separator, value = line.partition(":")
            if separator:
                headers[name.strip().lower()] = value.strip()

        expected = base64.b64encode(
            hashlib.sha1((key + _WEBSOCKET_GUID).encode("ascii")).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            raise ObsError("reponse WebSocket OBS non authentique")

    def _authentication(self, challenge: str, salt: str) -> str:
        secret = base64.b64encode(
            hashlib.sha256((self.config.password + salt).encode("utf-8")).digest()
        ).decode("ascii")
        return base64.b64encode(
            hashlib.sha256((secret + challenge).encode("utf-8")).digest()
        ).decode("ascii")

    # --- Requetes OBS ---------------------------------------------------------

    def request(self, request_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._socket is None:
            self.connect()

        request_id = uuid.uuid4().hex
        payload: dict[str, Any] = {
            "requestType": request_type,
            "requestId": request_id,
        }
        if data:
            payload["requestData"] = data

        self._send_json({"op": 6, "d": payload})

        while True:
            message = self._receive_json()
            if message.get("op") != 7:
                # Les evenements sont normalement desactives, mais les ignorer
                # rend le client tolerant a une version d'OBS plus bavarde.
                continue

            response = message.get("d")
            if not isinstance(response, dict) or response.get("requestId") != request_id:
                continue

            status = response.get("requestStatus")
            if not isinstance(status, dict) or not status.get("result"):
                comment = status.get("comment") if isinstance(status, dict) else ""
                code = status.get("code") if isinstance(status, dict) else "?"
                detail = str(comment or f"code {code}")
                raise ObsError(f"OBS a refuse {request_type} : {detail}")

            response_data = response.get("responseData", {})
            return response_data if isinstance(response_data, dict) else {}

    def status(self) -> ObsStatus:
        version = self.request("GetVersion")
        scene_list = self.request("GetSceneList")
        scenes = [
            item.get("sceneName", "")
            for item in scene_list.get("scenes", [])
            if isinstance(item, dict) and item.get("sceneName")
        ]
        return ObsStatus(
            obs_version=str(version.get("obsVersion", "")),
            websocket_version=str(version.get("obsWebSocketVersion", "")),
            scenes=scenes,
            current_scene=str(scene_list.get("currentProgramSceneName", "")),
        )

    # --- Trames WebSocket -----------------------------------------------------

    def _send_json(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_frame(0x1, data)

    def _receive_json(self) -> dict[str, Any]:
        payload = self._receive_message()
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ObsError(f"message JSON OBS illisible : {error}") from error
        if not isinstance(decoded, dict):
            raise ObsError("OBS a renvoye un message JSON inattendu")
        return decoded

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        if self._socket is None:
            raise ObsError("connexion OBS fermee")

        mask = os.urandom(4)
        length = len(payload)
        if length < 126:
            header = bytes((0x80 | opcode, 0x80 | length))
        elif length <= 0xFFFF:
            header = bytes((0x80 | opcode, 0x80 | 126)) + struct.pack("!H", length)
        else:
            header = bytes((0x80 | opcode, 0x80 | 127)) + struct.pack("!Q", length)

        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        try:
            self._socket.sendall(header + mask + masked)
        except OSError as error:
            raise ObsError(f"envoi vers OBS impossible : {error}") from error

    def _receive_message(self) -> bytes:
        fragments = bytearray()
        started = False

        while True:
            first, payload = self._receive_frame()
            final = bool(first & 0x80)
            opcode = first & 0x0F

            if opcode == 0x8:
                reason = ""
                if len(payload) > 2:
                    reason = payload[2:].decode("utf-8", "replace")
                raise ObsError(f"OBS a ferme la connexion{f' : {reason}' if reason else ''}")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x1:
                fragments.extend(payload)
                started = True
            elif opcode == 0x0 and started:
                fragments.extend(payload)
            else:
                raise ObsError(f"trame WebSocket OBS inattendue ({opcode})")

            if len(fragments) > _MAX_MESSAGE:
                raise ObsError("message OBS trop grand")
            if final:
                return bytes(fragments)

    def _receive_frame(self) -> tuple[int, bytes]:
        first, second = self._read_exact(2)
        length = second & 0x7F
        masked = bool(second & 0x80)

        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        if length > _MAX_MESSAGE:
            raise ObsError("trame OBS trop grande")

        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length)
        if mask:
            payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        return first, payload

    def _read_exact(self, size: int) -> bytes:
        if self._socket is None:
            raise ObsError("connexion OBS fermee")
        while len(self._buffer) < size:
            try:
                chunk = self._socket.recv(max(4096, size - len(self._buffer)))
            except OSError as error:
                raise ObsError(f"lecture depuis OBS impossible : {error}") from error
            if not chunk:
                raise ObsError("OBS a ferme la connexion")
            self._buffer.extend(chunk)
        payload = bytes(self._buffer[:size])
        del self._buffer[:size]
        return payload

    def close(self) -> None:
        sock = self._socket
        self._socket = None
        if sock is None:
            return
        try:
            sock.close()
        except OSError:
            pass


def test_connection(config: ObsConfig) -> ObsStatus:
    """Verifie l'identification et renvoie les scenes disponibles."""
    with ObsClient(config) as client:
        return client.status()


"""Durable, individually revocable console credentials.

The console receives a bearer credential once.  Only its SHA-256 digest is
stored locally, so neither the HTTP state endpoint nor a copied registry file
can disclose usable console credentials.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Awaitable, Callable

from .errors import ServiceError
from .executor import WorkPool

REGISTRY_VERSION = 1
MAX_PAIRED_DEVICES = 64
DEVICE_ID = re.compile(r"^[0-9a-f]{16}$")
TOKEN = re.compile(r"^d3d_([0-9a-f]{16})\.([A-Za-z0-9_-]{32})$")


class DeviceStoreError(RuntimeError):
    """The credential registry cannot be read or committed safely."""


@dataclass
class _Device:
    id: str
    name: str
    secret_hash: str
    created_at: str
    last_seen: str

    def public(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "last_seen": self.last_seen,
        }


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _device_name(value: object) -> str:
    if not isinstance(value, str):
        return "Console 3DS"
    candidate = " ".join(value.strip().split())
    if not candidate or any(ord(char) < 32 or ord(char) == 127 for char in candidate):
        return "Console 3DS"
    return candidate[:64]


def _secret_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode("ascii")).hexdigest()


def _load(path: Path) -> dict[str, _Device]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("version") != REGISTRY_VERSION:
            raise ValueError("unsupported registry version")
        records = raw.get("devices")
        if not isinstance(records, list) or len(records) > MAX_PAIRED_DEVICES:
            raise ValueError("invalid device collection")
        devices: dict[str, _Device] = {}
        for item in records:
            if not isinstance(item, dict) or set(item) != {
                "id",
                "name",
                "secret_hash",
                "created_at",
                "last_seen",
            }:
                raise ValueError("invalid device record")
            device = _Device(**item)
            if (
                not DEVICE_ID.fullmatch(device.id)
                or not 1 <= len(device.name) <= 64
                or not re.fullmatch(r"[0-9a-f]{64}", device.secret_hash)
                or not device.created_at.endswith("Z")
                or not device.last_seen.endswith("Z")
                or device.id in devices
            ):
                raise ValueError("invalid device fields")
            devices[device.id] = device
        return devices
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise DeviceStoreError(f"registre de consoles invalide: {path}") from error


def _save(path: Path, devices: dict[str, _Device]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "version": REGISTRY_VERSION,
        "devices": [
            asdict(device) for device in sorted(devices.values(), key=lambda item: item.id)
        ],
    }
    text = json.dumps(body, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            # Windows ACLs are authoritative; chmod is best-effort there.
            pass
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except OSError as error:
        raise DeviceStoreError("ecriture du registre de consoles impossible") from error
    finally:
        temporary.unlink(missing_ok=True)


class DeviceService:
    def __init__(
        self,
        path: Path | None,
        pool: WorkPool,
        disconnect: Callable[[str], Awaitable[None]],
        log: Callable[[str], None],
    ) -> None:
        self.path = path
        self._pool = pool
        self._disconnect = disconnect
        self._log = log
        self._devices: dict[str, _Device] = {}
        self._lock = asyncio.Lock()
        self._loaded = False

    async def start(self) -> None:
        async with self._lock:
            if self._loaded:
                return
            if self.path is not None:
                self._devices = await self._pool.run(_load, self.path)
            self._loaded = True

    def snapshot(self) -> list[dict[str, str]]:
        return [
            device.public()
            for device in sorted(
                self._devices.values(), key=lambda item: item.last_seen, reverse=True
            )
        ]

    async def _commit(self) -> None:
        if self.path is not None:
            await self._pool.run(_save, self.path, self._devices)

    async def issue(self, name: object) -> tuple[str, dict[str, str]]:
        await self.start()
        async with self._lock:
            if len(self._devices) >= MAX_PAIRED_DEVICES:
                raise DeviceStoreError("limite de consoles appairees atteinte")
            while True:
                device_id = secrets.token_hex(8)
                if device_id not in self._devices:
                    break
            secret = secrets.token_urlsafe(24)
            stamp = _now()
            device = _Device(
                id=device_id,
                name=_device_name(name),
                secret_hash=_secret_hash(secret),
                created_at=stamp,
                last_seen=stamp,
            )
            self._devices[device_id] = device
            try:
                await self._commit()
            except BaseException:
                self._devices.pop(device_id, None)
                raise
            return f"d3d_{device_id}.{secret}", device.public()

    async def authenticate(self, token: object, name: object) -> dict[str, str] | None:
        await self.start()
        if not isinstance(token, str):
            return None
        match = TOKEN.fullmatch(token)
        if match is None:
            return None
        device_id, secret = match.groups()
        async with self._lock:
            device = self._devices.get(device_id)
            if device is None or not hmac.compare_digest(
                device.secret_hash, _secret_hash(secret)
            ):
                return None
            previous_seen, previous_name = device.last_seen, device.name
            device.last_seen = _now()
            device.name = _device_name(name)
            try:
                await self._commit()
            except BaseException:
                device.last_seen, device.name = previous_seen, previous_name
                raise
            return device.public()

    async def revoke(self, device_id: str) -> dict[str, bool]:
        await self.start()
        if DEVICE_ID.fullmatch(device_id) is None:
            raise ServiceError(404, "console appairee introuvable", "device_not_found")
        async with self._lock:
            removed = self._devices.pop(device_id, None)
            if removed is None:
                raise ServiceError(404, "console appairee introuvable", "device_not_found")
            try:
                await self._commit()
            except BaseException:
                self._devices[device_id] = removed
                raise
        await self._disconnect(device_id)
        self._log(f"Paired console revoked: {removed.name}")
        return {"revoked": True}

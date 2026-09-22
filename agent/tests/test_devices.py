from __future__ import annotations

import stat
import sys

import pytest

from deck3ds.services.devices import DeviceService, DeviceStoreError
from deck3ds.services.executor import WorkPool

pytestmark = pytest.mark.asyncio


async def test_credentials_are_hashed_persisted_and_individually_revocable(tmp_path):
    disconnected: list[str] = []

    async def disconnect(device_id: str) -> None:
        disconnected.append(device_id)

    pool = WorkPool("test-devices", workers=1)
    path = tmp_path / "paired-consoles.json"
    service = DeviceService(path, pool, disconnect, lambda _message: None)
    try:
        credential, device = await service.issue("  New   3DS XL  ")
        assert device["name"] == "New 3DS XL"
        stored = path.read_text(encoding="utf-8")
        assert credential not in stored
        assert credential.rsplit(".", 1)[1] not in stored
        if sys.platform != "win32":
            assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0

        reloaded = DeviceService(path, pool, disconnect, lambda _message: None)
        authenticated = await reloaded.authenticate(credential, "Console salon")
        assert authenticated is not None
        assert authenticated["id"] == device["id"]
        assert authenticated["name"] == "Console salon"
        assert await reloaded.authenticate(credential + "x", "forged") is None

        assert await reloaded.revoke(device["id"]) == {"revoked": True}
        assert disconnected == [device["id"]]
        assert await reloaded.authenticate(credential, "Console salon") is None
    finally:
        await pool.close()


async def test_invalid_registry_fails_closed(tmp_path):
    path = tmp_path / "paired-consoles.json"
    path.write_text('{"version":1,"devices":[{"id":"bad"}]}', encoding="utf-8")
    pool = WorkPool("test-invalid-devices", workers=1)
    service = DeviceService(path, pool, lambda _id: None, lambda _message: None)
    try:
        with pytest.raises(DeviceStoreError):
            await service.start()
    finally:
        await pool.close()


async def test_api_lists_and_revokes_device(agent, client):
    credential, device = await agent.services.devices.issue("Ma 3DS")
    state = (await client.get("/api/state")).json()
    assert state["paired_devices"] == [device]
    assert credential not in str(state)

    response = await client.delete(f"/api/paired-devices/{device['id']}")
    assert response.status_code == 200
    assert response.json() == {"revoked": True}
    assert (await client.get("/api/state")).json()["paired_devices"] == []

    missing = await client.delete(f"/api/paired-devices/{device['id']}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "device_not_found"

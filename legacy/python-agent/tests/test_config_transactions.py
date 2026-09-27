"""Real files and simultaneous callers exercise the sole mutation boundary."""

import asyncio
import copy
import json
import threading
from unittest.mock import patch

import pytest

from deck3ds import config
from deck3ds.configuration.storage import save
from deck3ds.services.configuration import fingerprint
from deck3ds.services.errors import ServiceError

pytestmark = pytest.mark.asyncio


async def test_simultaneous_saves_have_one_winner(agent):
    service = agent.services.config
    document = service.document()["config"]
    results = await asyncio.gather(
        service.save(document), service.save(document), return_exceptions=True
    )
    assert sum(isinstance(result, dict) for result in results) == 1
    conflict = next(result for result in results if isinstance(result, ServiceError))
    assert conflict.status == 409
    assert service.current.revision == document["revision"] + 1


async def test_external_edit_conflicts_then_reload_uses_same_service(agent):
    service = agent.services.config
    document = service.document()["config"]
    external = copy.deepcopy(document)
    external["pages"][0]["title"] = "External"
    service.path.write_text(json.dumps(external), encoding="utf-8")
    with pytest.raises(ServiceError, match="change") as error:
        await service.save(document)
    assert error.value.code == "config_conflict"
    assert await service.reload_if_changed()
    assert service.current.pages[0].title("en") == "External"
    assert agent.config.pages[0].title("en") == "External"
    assert not await service.reload_if_changed()
    await service.save(service.document()["config"])


async def test_invalid_external_file_preserves_memory_and_conflicts(agent):
    service = agent.services.config
    original = service.document()
    service.path.write_text("{invalid", encoding="utf-8")
    assert not await service.reload_if_changed()
    assert not await service.reload_if_changed()
    assert service.document() == original
    with pytest.raises(ServiceError) as error:
        await service.save(original["config"])
    assert error.value.status == 409
    service.path.unlink()
    assert fingerprint(service.path) == "missing"
    assert not await service.reload_if_changed()


async def test_disk_error_keeps_memory_file_and_temp_directory_intact(agent):
    service = agent.services.config
    original = service.path.read_bytes()
    with patch("pathlib.Path.replace", side_effect=OSError("disk unavailable")):
        with pytest.raises(ServiceError) as error:
            await service.save(service.document()["config"])
    assert error.value.code == "config_write_failed"
    assert service.path.read_bytes() == original
    assert service.current.revision == json.loads(original)["revision"]
    assert not list(service.path.parent.glob(".*.tmp"))


async def test_abandoned_request_does_not_cancel_commit(agent):
    service = agent.services.config
    entered, release = threading.Event(), threading.Event()

    def slow_save(*args):
        entered.set()
        assert release.wait(2)
        return save(*args)

    with patch.object(config, "save", slow_save):
        request = asyncio.create_task(service.save(service.document()["config"]))
        try:
            while not entered.is_set():
                await asyncio.sleep(0.001)
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
            shutdown = asyncio.create_task(service.close())
            await asyncio.sleep(0.01)
            assert not shutdown.done()
        finally:
            release.set()
        await shutdown
    assert service.current.revision == 2
    assert not service._pending
    with pytest.raises(ServiceError) as error:
        await service.save({})
    assert error.value.status == 503


async def test_external_edit_after_replace_is_not_accidentally_accepted(agent):
    service = agent.services.config

    def write_then_external_edit(configuration, path):
        digest = save(configuration, path)
        path.write_text('{"pages":[]}', encoding="utf-8")
        return digest

    with patch.object(config, "save", write_then_external_edit):
        await service.save(service.document()["config"])
    with pytest.raises(ServiceError) as error:
        await service.save(service.document()["config"])
    assert error.value.code == "config_conflict"


async def test_broadcast_failure_does_not_undo_a_commit(agent):
    service = agent.services.config

    async def disconnected():
        raise ConnectionResetError

    service._publish = disconnected
    result = await service.save(service.document()["config"])
    assert result["saved"]
    assert config.load(service.path).revision == service.current.revision


async def test_console_resolution_never_mutates_persisted_document(agent):
    service = agent.services.config
    raw = service.document()["config"]
    raw["pages"][0].update(source="windows", buttons=[])
    await service.save(raw)
    assert agent.config.pages[0].buttons
    assert not service.current.pages[0].buttons
    assert not service.document()["config"]["pages"][0]["buttons"]
    assert not config.load(service.path).pages[0].buttons


async def test_validation_never_writes_and_has_clear_shape_errors(agent):
    service = agent.services.config
    previous = service.path.read_bytes()
    assert service.validate({"pages": []})["valid"] is False
    assert service.path.read_bytes() == previous
    with pytest.raises(ServiceError) as error:
        service.validate([])
    assert error.value.status == 400
    service.path = None
    assert not await service.reload_if_changed()
    with pytest.raises(ServiceError) as error:
        await service.save({})
    assert error.value.code == "no_config_file"

"""Service failures, isolation and thread accounting without FastAPI dependencies."""

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from deck3ds.extensions.manifest import ExtensionError
from deck3ds.obs import ObsError
from deck3ds.platforms.base import ActionFailed, SelectionCancelled, Unsupported
from deck3ds.services.errors import ServiceError
from deck3ds.services.executor import WorkPool

pytestmark = pytest.mark.asyncio


async def test_state_reads_are_cached_and_independent(agent):
    state = agent.services.state
    await state.refresh_metadata()
    agent.platform.snapshot = Mock(side_effect=AssertionError("native call from HTTP"))
    agent.platform.capabilities = Mock(side_effect=AssertionError("not cached"))
    agent.platform.notification_status = Mock(side_effect=AssertionError("not cached"))
    first = state.read()
    first["snapshot"]["injected"] = True
    assert "injected" not in state.read()["snapshot"]
    assert state.schema()["actions"]
    await state.refresh_metadata()
    state.rotate_pairing()


async def test_platform_errors_keep_service_contracts(agent):
    system = agent.services.system
    for kind in ("command", ""):
        with pytest.raises(ServiceError) as error:
            await system.pick(kind)
        assert error.value.status == 422
    for failure in (Unsupported("not supported"), ActionFailed("failed")):
        agent.platform.choose_path = Mock(side_effect=failure)
        with pytest.raises(ServiceError) as error:
            await system.pick("file")
        assert error.value.code == "selection_unavailable"
        agent.platform.open_permission_settings = Mock(side_effect=failure)
        with pytest.raises(ServiceError) as error:
            await system.permission("notifications")
        assert error.value.code == "permission_unavailable"
    with pytest.raises(ServiceError) as error:
        await system.permission("")
    assert error.value.code == "invalid_permission"
    with pytest.raises(ServiceError) as error:
        await system.obs({"port": 0})
    assert error.value.code == "invalid_obs_config"
    with patch(
        "deck3ds.services.system.test_connection", side_effect=ObsError("offline")
    ):
        with pytest.raises(ServiceError) as error:
            await system.obs({})
    assert error.value.code == "obs_unavailable"
    payload = {"connected": True, "scenes": ["Camera"], "current_scene": "Camera"}
    with patch(
        "deck3ds.services.system.test_connection",
        return_value=SimpleNamespace(as_payload=lambda: payload),
    ):
        assert await system.obs({}) == payload


@pytest.mark.parametrize(
    "operation,values,method,args",
    [
        ("rescan", {}, "rescan", ()),
        ("enable", {"trust": True, "digest": "hash"}, "enable", ("test", True, "hash")),
        ("disable", {}, "enable", ("test", False)),
        (
            "configure",
            {"settings": {"name": "value"}},
            "configure",
            ("test", {"name": "value"}),
        ),
        ("restart", {}, "restart", ("test",)),
        ("remove", {"confirm": True}, "remove", ("test",)),
    ],
)
async def test_extension_operations_are_explicit(
    agent, operation, values, method, args
):
    service = agent.services.extensions
    manager = service.manager = Mock()
    assert await service.manage({"operation": operation, "id": "test", **values}) == {
        "ok": True
    }
    getattr(manager, method).assert_called_once_with(*args)


@pytest.mark.parametrize(
    "payload",
    [
        {"id": 3},
        {"operation": "execute"},
        {"operation": "enable"},
        {"operation": "configure", "settings": []},
        {"operation": "remove", "confirm": False},
    ],
)
async def test_invalid_extension_operation_never_runs(agent, payload):
    service = agent.services.extensions
    manager = service.manager = Mock()
    with pytest.raises(ServiceError) as error:
        await service.manage(payload)
    assert error.value.status == 422
    assert not manager.mock_calls


async def test_extension_install_only_uses_native_selection(agent, tmp_path):
    service = agent.services.extensions
    manager = service.manager = Mock()
    selected = tmp_path / "extension.zip"
    agent.platform.choose_path = Mock(return_value=str(selected))
    assert await service.manage({"operation": "install"}) == {"ok": True}
    manager.install.assert_called_once_with(selected)
    agent.platform.choose_path = Mock(side_effect=SelectionCancelled())
    assert await service.manage({"operation": "install"}) == {"cancelled": True}
    manager.rescan.side_effect = ExtensionError("bad manifest")
    with pytest.raises(ServiceError) as error:
        await service.manage({"operation": "rescan"})
    assert error.value.code == "extension_operation_failed"


async def test_slow_dialog_does_not_block_reads_or_native_collection(agent, client):
    entered, release = threading.Event(), threading.Event()

    def choose(_kind):
        entered.set()
        assert release.wait(2)
        return "/selected"

    agent.platform.choose_path = choose
    request = asyncio.create_task(client.post("/api/paths/pick", json={"kind": "file"}))
    try:
        while not entered.is_set():
            await asyncio.sleep(0.001)
        assert (
            await asyncio.wait_for(client.get("/api/state"), 0.5)
        ).status_code == 200
        assert (
            await asyncio.wait_for(agent.native_pool.run(lambda: "collect"), 0.5)
            == "collect"
        )
    finally:
        release.set()
    assert (await request).json()["path"] == "/selected"


async def test_timeout_keeps_actual_work_counted_until_completion():
    pool = WorkPool("test-bounded", workers=1, capacity=1)
    entered, release = threading.Event(), threading.Event()
    second_ran = threading.Event()

    def first_job():
        entered.set()
        assert release.wait(2)

    first = asyncio.create_task(pool.run(first_job))
    try:
        while not entered.is_set():
            await asyncio.sleep(0.001)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        second = asyncio.create_task(pool.run(second_ran.set))
        await asyncio.sleep(0.01)
        assert not second_ran.is_set()
        assert len(pool._pending) == 1
        closing = asyncio.create_task(pool.close())
        await asyncio.sleep(0.01)
        assert not closing.done()
    finally:
        release.set()
    await closing
    with pytest.raises(RuntimeError, match="stopping"):
        await second
    with pytest.raises(RuntimeError, match="stopping"):
        await pool.run(lambda: None)
    assert not pool._pending


async def test_work_submission_failure_releases_capacity():
    pool = WorkPool("failed-submission", workers=1, capacity=1)
    try:
        with patch(
            "asyncio.BaseEventLoop.run_in_executor",
            side_effect=RuntimeError("executor failed"),
        ):
            with pytest.raises(RuntimeError):
                await pool.run(lambda: None)
        assert await asyncio.wait_for(pool.run(lambda: 42), 1) == 42
    finally:
        await pool.close()


async def test_finalizer_failure_still_closes_executor():
    pool = WorkPool("finalizer", workers=1)
    with pytest.raises(RuntimeError):
        await pool.close(Mock(side_effect=RuntimeError("native shutdown failed")))
    assert pool._pool is None

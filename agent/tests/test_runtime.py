"""Real sockets and owned tasks, with fake platform adapters only."""

import asyncio
import signal
import socket
import threading
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from deck3ds import protocol
from deck3ds.config import Action
from deck3ds.api.server import UiServer
from deck3ds.runtime.signals import run_agent

pytestmark = pytest.mark.asyncio


async def start_runtime(agent, ui=None):
    agent.config.host, agent.config.port = "127.0.0.1", 0
    agent.ui_port = ui
    agent._start_discovery = AsyncMock()
    task = asyncio.create_task(agent.start())
    for _ in range(300):
        if task.done():
            await task
            raise AssertionError("runtime unexpectedly exited")
        if agent._tasks:
            return task
        await asyncio.sleep(0.005)
    raise AssertionError("startup timed out")


@pytest.mark.parametrize("ui", [None, 0])
async def test_lifecycle_keeps_clients_and_stops_everything(agent, ui):
    opened = []
    agent.on_ui_ready = opened.append
    task = await start_runtime(agent, ui)
    reader, writer = await asyncio.open_connection(
        "127.0.0.1", agent._server.sockets[0].getsockname()[1]
    )
    writer.write(protocol.encode({"type": "hello", "protocol": 1, "device": "test"}))
    await writer.drain()
    assert await asyncio.wait_for(reader.read(65536), 1)
    if ui is not None:
        assert opened == [agent._ui.url]
        async with httpx.AsyncClient() as browser:
            response = await browser.get(agent._ui.url + "&ignored=1")
            assert response.status_code == 200
            response = await browser.get(
                f"http://127.0.0.1:{agent._ui.port}/api/health",
                headers={"X-Deck3DS-Token": agent._ui.token},
            )
            assert response.json()["components"]["http"] == "ready"
    else:
        assert opened == []
        assert agent.health()["components"]["http"] == "disabled"
    agent.request_stop()
    await asyncio.wait_for(task, 3)
    assert agent._closed
    assert not agent.clients
    assert not agent._client_tasks
    assert all(task.done() for task in agent._tasks)
    assert not agent._server.is_serving()
    await agent.close()
    writer.close()
    await writer.wait_closed()


async def test_ui_port_busy_is_nonfatal_for_console(agent):
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        task = await start_runtime(agent, occupied.getsockname()[1])
        assert agent._server.is_serving()
        assert agent._ui is None
        assert agent.health()["status"] == "degraded"
        agent.request_stop()
        await asyncio.wait_for(task, 2)


async def test_tcp_port_busy_cleans_partial_startup(agent):
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        agent.config.host, agent.config.port = occupied.getsockname()
        with pytest.raises(OSError):
            await agent.start()
    assert agent._closed
    assert not agent._tasks


async def test_discovery_start_failure_cleans_tcp_and_platform(agent):
    agent.config.host, agent.config.port = "127.0.0.1", 0
    agent._start_discovery = AsyncMock(side_effect=RuntimeError("partial startup"))
    closed = agent.platform.close = Mock()
    with pytest.raises(RuntimeError):
        await agent.start()
    assert agent._closed
    assert not agent._server.is_serving()
    closed.assert_called_once()


async def test_background_failure_is_supervised(agent):
    agent.config.host, agent.config.port = "127.0.0.1", 0
    agent._start_discovery = AsyncMock()
    agent._poll_forever = AsyncMock(side_effect=RuntimeError("collect failed"))
    with pytest.raises(RuntimeError):
        await agent.start()
    assert agent._closed
    assert "Collecte interrompue" in " ".join(agent.recent_logs())


async def test_cancellation_closes_runtime_and_rejects_restart(agent):
    task = await start_runtime(agent)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 2)
    assert agent._closed
    with pytest.raises(RuntimeError, match="once"):
        await agent.start()


async def test_browser_failure_does_not_prevent_startup(agent):
    agent.on_ui_ready = Mock(side_effect=RuntimeError("no browser"))
    task = await start_runtime(agent, 0)
    assert agent._ui.running
    agent.request_stop()
    await asyncio.wait_for(task, 3)


async def test_shutdown_continues_after_native_cleanup_failure(agent):
    agent.platform.close = Mock(side_effect=RuntimeError("native failure"))
    await agent.close()
    assert agent._closed
    assert agent.operations_pool._pool is None
    assert "nettoyage" in " ".join(agent.recent_logs())


async def test_shutdown_drains_extension_operations_before_final_cleanup(agent):
    started, release = threading.Event(), threading.Event()
    order = []

    def operation():
        started.set()
        assert release.wait(2)
        order.append("enabled")

    agent.extensions.close = lambda: order.append("closed")
    pending = asyncio.create_task(agent.extension_pool.run(operation))
    closing = None
    try:
        while not started.is_set():
            await asyncio.sleep(0.001)
        closing = asyncio.create_task(agent.close())
        await asyncio.sleep(0.02)
        assert not closing.done()
        assert "closed" not in order
    finally:
        release.set()
        await pending
        if closing is not None:
            await closing
    assert order == ["enabled", "closed"]
    assert agent.extension_pool._pool is None


async def test_find_addresses_handles_unavailable_network(agent):
    with patch("deck3ds.runtime.agent.socket.socket", side_effect=OSError("offline")):
        assert agent.find_addresses() == []


async def test_native_read_modify_write_actions_are_serialized(agent):
    original = agent.platform.get_volume

    def delayed_volume():
        time.sleep(0.02)
        return original()

    agent.platform.get_volume = delayed_volume
    await asyncio.gather(
        agent.actions_pool.run(agent.dispatcher.run, Action("volume.up", {"step": 5})),
        agent.actions_pool.run(agent.dispatcher.run, Action("volume.up", {"step": 5})),
    )
    assert agent.platform.volume == 50
    assert agent.platform.calls[-2:] == ["set_volume:45", "set_volume:50"]


async def test_signal_owner_works_without_ui_and_restores_handlers(agent):
    previous = {
        kind: signal.getsignal(kind) for kind in (signal.SIGINT, signal.SIGTERM)
    }

    async def fake_start():
        # Invoke the installed callback without signalling the test process.
        callback = signal.getsignal(signal.SIGTERM)
        callback(signal.SIGTERM, None)
        await asyncio.sleep(0)
        assert agent._stop.is_set()

    agent.start = fake_start
    await run_agent(agent)
    assert {kind: signal.getsignal(kind) for kind in previous} == previous
    assert agent._closed


async def test_ui_duplicate_start_and_failed_startup_cleanup(agent):
    ui = UiServer(agent.services, port=0)
    try:
        await ui.start()
        with pytest.raises(RuntimeError):
            await ui.start()
    finally:
        await ui.close()
    failed = UiServer(agent.services, port=0)
    with patch(
        "deck3ds.api.server.EmbeddedServer.startup",
        side_effect=RuntimeError("startup failure"),
    ):
        with pytest.raises(RuntimeError):
            await failed.start()
    assert failed._socket is None


async def test_real_udp_discovery_preserves_protocol(agent):
    with patch("deck3ds.transports.discovery.DISCOVERY_PORT", 0):
        await agent._start_discovery()
    port = agent._discovery_transport.get_extra_info("sockname")[1]
    loop = asyncio.get_running_loop()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as console:
        console.setblocking(False)
        import json

        request = json.dumps(
            {"type": "deck3ds.discover", "protocol": 1, "nonce": 42}
        ).encode()
        await loop.sock_sendto(console, request, ("127.0.0.1", port))
        reply, _ = await asyncio.wait_for(loop.sock_recvfrom(console, 512), 1)
    payload = json.loads(reply)
    assert payload["type"] == "deck3ds.agent"
    assert payload["protocol"] == 1
    assert payload["nonce"] == 42
    assert "token" not in payload

"""Order resource ownership explicitly, including partial startup failures."""

from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from .agent import AgentRuntime


class Lifecycle:
    def __init__(self, owner: AgentRuntime) -> None:
        self.owner = owner

    async def start(self) -> None:
        agent = self.owner
        if agent._closed or agent._server is not None:
            raise RuntimeError("An agent runtime can only be started once")
        try:
            # Credentials must be loaded before accepting a TCP handshake.
            await agent.services.devices.start()
            agent._server = await asyncio.start_server(
                agent._handle_client, agent.config.host, agent.config.port
            )
            agent._addresses = await agent.native_pool.run(agent.find_addresses)
            agent.log(
                f"Agent 3Decks {agent.version} en ecoute sur le port {agent.config.port}"
            )
            await agent._start_discovery()
            await self.start_ui()
            agent._tasks = [
                asyncio.create_task(agent._poll_loop(), name="agent-collector"),
                asyncio.create_task(agent.extensions.run(), name="agent-extensions"),
            ]
            stop = asyncio.create_task(agent._stop.wait(), name="agent-stop")
            try:
                done, _ = await asyncio.wait(
                    [*agent._tasks, stop], return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    await task
            finally:
                stop.cancel()
                await asyncio.gather(stop, return_exceptions=True)
        except asyncio.CancelledError:
            raise
        finally:
            await agent.close()

    async def start_ui(self) -> None:
        agent = self.owner
        if agent.ui_port is None:
            return
        from ..api.server import UiServer

        ui = UiServer(
            agent.services,
            port=agent.ui_port,
            dev_origins=agent.ui_dev_origins,
            log=agent.log,
        )
        try:
            await ui.start()
        except (OSError, RuntimeError):
            await ui.close()
            agent.log(
                f"Interface indisponible sur le port {agent.ui_port}; la console reste utilisable"
            )
            return
        agent._ui = ui
        if agent.on_ui_ready:
            try:
                await agent.operations_pool.run(agent.on_ui_ready, ui.url)
            except Exception:
                agent.debug("Ouverture automatique du navigateur impossible")

    async def close(self) -> None:
        agent = self.owner
        agent._closing = True
        agent.services.config.stop_admissions()
        if agent._ui:
            agent._ui.stop_admissions()

        async def finish(label: str, operation: Callable[[], Awaitable[None]]) -> None:
            try:
                await operation()
            except Exception as error:
                agent.log(
                    f"Arret {label}: {type(error).__name__}; nettoyage des autres ressources poursuivi"
                )

        if agent._server:
            agent._server.close()
        agent._stop_discovery()
        await finish(
            "dialogues", lambda: agent.operations_pool.run(agent.platform.close_dialogs)
        )
        if agent._ui:
            await finish("HTTP", agent._ui.close)
        for task in agent._tasks:
            task.cancel()
        await asyncio.gather(*agent._tasks, return_exceptions=True)
        await finish("configuration", agent.services.config.close)
        await asyncio.gather(
            *(client.close() for client in list(agent.clients)), return_exceptions=True
        )
        for task in list(agent._client_tasks):
            task.cancel()
        await asyncio.gather(*agent._client_tasks, return_exceptions=True)
        if agent._server:
            await agent._server.wait_closed()
        await finish(
            # An admitted enable/install may still be running after its HTTP
            # caller was cancelled. Drain it before the final process cleanup.
            "extensions", lambda: agent.extension_pool.close(agent.extensions.close)
        )
        for pool in (
            agent.dialog_pool,
            agent.actions_pool,
            agent.native_pool,
            agent.io_pool,
            agent.extension_actions_pool,
        ):
            await finish("operations", pool.close)
        await finish(
            "plateforme", lambda: agent.operations_pool.close(agent.platform.close)
        )
        agent.clients.clear()
        agent._closed = True

"""Single-process composition root; the HTTP adapter is an optional consumer."""

from __future__ import annotations
import asyncio
import copy
import math
import socket
import time
from collections import Counter, deque
from typing import Any, Awaitable, Callable, TYPE_CHECKING
from ..actions import Dispatcher
from ..config import Config
from ..extensions.manager import ExtensionManager
from ..pairing import PairingManager
from ..platforms.base import Platform
from ..services.bundle import Services
from ..services.configuration import ConfigService
from ..services.devices import DeviceService
from ..services.executor import WorkPool
from ..services.extensions import ExtensionService
from ..services.state import StateService
from ..services.system import SystemService
from ..transports.configuration import ConsoleConfiguration
from ..transports.parts import ArtworkCache, Client, Options
from ..version import VERSION
from ..transports.broadcast import Broadcast
from ..transports.collect import Collect
from ..transports.commands import Command
from ..transports.connection import Connection
from ..transports.handshake import Handshake
from ..transports.discovery import Discovery
from ..transports.logs import Logging

from .lifecycle import Lifecycle

if TYPE_CHECKING:
    from ..api.server import UiServer


class AgentRuntime:
    services: Services
    log: Callable[[str], None]
    debug: Callable[[str], None]
    _handle_client: Callable[
        [asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]
    ]
    _start_discovery: Callable[[], Awaitable[None]]
    _stop_discovery: Callable[[], None]

    def __init__(
        self, config: Config, platform: Platform, options: Options | None = None
    ) -> None:
        options = options or Options()
        self.config = copy.deepcopy(config)
        self.platform = platform
        self.platform.configure_features(config.features)
        self.config_path = options.config_path
        self.verbose = options.verbose
        self.version = VERSION
        self.ui_port = options.ui_port
        self.ui_dev_origins = options.ui_dev_origins
        self.on_ui_ready: Callable[[str], None] | None = None
        self.clients: set[Client] = set()
        self._client_tasks: set[asyncio.Task[None]] = set()
        self._logs: deque[str] = deque(maxlen=300)
        self._events: deque[dict[str, Any]] = deque(maxlen=300)
        self._counters: Counter[str] = Counter()
        self._last_payload: dict[str, Any] | None = None
        self._refresh_event: asyncio.Event | None = None
        self._slow_confirm = False
        self._published_windows: list[tuple[str, str]] = []
        self._artwork = ArtworkCache()
        self._server: asyncio.Server | None = None
        self._discovery_transport: asyncio.DatagramTransport | None = None
        self._discovery_name = ""
        self._addresses: list[str] = []
        self._ui: UiServer | None = None
        self._tasks: list[asyncio.Task[None]] = []
        self._stop = asyncio.Event()
        self._controls_paused_until: float | None = None
        self._closing = False
        self._closed = False
        self._close_task: asyncio.Task[None] | None = None
        self.started_at = time.monotonic()
        self.last_collection_at: float | None = None
        self.native_pool = WorkPool("3decks-collect", workers=2, capacity=4)
        # Native actions share mutable OS state (volume, mute, focused window).
        # Preserve command order and make read/modify/write actions atomic from
        # the agent's point of view. Extension actions keep their own pool.
        self.actions_pool = WorkPool("3decks-action", workers=1, capacity=8)
        self.io_pool = WorkPool("3decks-files", workers=1, capacity=4)
        self.operations_pool = WorkPool("3decks-operation", workers=2, capacity=8)
        self.dialog_pool = WorkPool("3decks-dialog", workers=1, capacity=1)
        self.extension_pool = WorkPool("3decks-extension-admin", workers=2, capacity=4)
        self.extension_actions_pool = WorkPool(
            "3decks-extension-action", workers=2, capacity=8
        )
        self._extensions = ExtensionManager(
            self.config_path.parent / "extensions" if self.config_path else None,
            platform.name,
        )
        self.dispatcher = Dispatcher(platform, self.config, self.extensions)
        self.pairing = PairingManager()
        self.broadcast = Broadcast(self)
        self._audience = self.broadcast._audience
        self._broadcast = self.broadcast._broadcast
        self._drop = self.broadcast._drop
        self._publish = self.broadcast._publish
        self.collect = Collect(self)
        self._wake = self.collect._wake
        self._wait_for_wake = self.collect._wait_for_wake
        self._collect_safely = self.collect._collect_safely
        self._confirm_after_action = self.collect._confirm_after_action
        self._poll_forever = self.collect._poll_forever
        self._refresh_state = self.collect._refresh_state
        self._republish_windows = self.collect._republish_windows
        self._refresh_artwork = self.collect._refresh_artwork
        self._delta_since_last = self.collect._delta_since_last
        self.last_state_payload = self.collect.last_state_payload
        self.commands = Command(self)
        self._resolve_target = self.commands._resolve_target
        self._run_action = self.commands._run_action
        self._schedule_confirmation = self.commands._schedule_confirmation
        self._handle_button = self.commands._handle_button
        self._handle_value = self.commands._handle_value
        self.connection = Connection(self)
        self._handle_client = self.connection._handle_client
        self._read_messages = self.connection._read_messages
        self._dispatch_available = self.connection._dispatch_available
        self._handle_message = self.connection._handle_message
        self._handle_ping = self.connection._handle_ping
        self._handle_config_request = self.connection._handle_config_request
        self.handshake = Handshake(self)
        self._accept_handshake = self.handshake._accept_handshake
        self._reject_handshake = self.handshake._reject_handshake
        self._send_initial_state = self.handshake._send_initial_state
        self._handle_hello = self.handshake._handle_hello
        self.discovery = Discovery(self)
        self.discovery_payload = self.discovery.discovery_payload
        self._start_discovery = self.discovery._start_discovery
        self._stop_discovery = self.discovery._stop_discovery
        self.logs = Logging(self)
        self.log = self.logs.log
        self.debug = self.logs.debug
        self.event = self.logs.event
        self.recent_logs = self.logs.recent_logs
        self.recent_events = self.logs.recent_events
        self.event_counters = self.logs.counters

        self.console_config = ConsoleConfiguration(self)
        self._has_dynamic_pages = self.console_config._has_dynamic_pages
        self._fill_dynamic_pages = self.console_config._fill_dynamic_pages
        self._config_message = self.console_config._config_message
        self._broadcast_config = self.console_config._broadcast_config
        configuration = ConfigService(
            config,
            self.config_path,
            self.io_pool,
            lambda candidate: self.extensions.validate_config(candidate),
            self._install_config,
            self.console_config.publish,
            lambda message: self.log(message),
        )
        devices = DeviceService(
            self.config_path.with_name("paired-consoles.json")
            if self.config_path
            else None,
            self.io_pool,
            self._disconnect_device,
            lambda message: self.log(message),
        )
        system = SystemService(platform, self.operations_pool, self.dialog_pool)
        state = StateService(
            configuration,
            platform,
            self.extensions,
            self.pairing,
            VERSION,
            # StateService owns the response copy; retain last_state_payload()
            # as the detached-copy API for other consumers.
            lambda: self._last_payload or {},
            self.client_summaries,
            lambda: self.local_addresses(),
            lambda: self.recent_logs(),
            lambda: self.recent_events(),
            lambda: self.event_counters(),
            devices.snapshot,
            self.health,
            lambda: {
                "paused": self.controls_paused,
                "pause_remaining": self.controls_pause_remaining,
            },
            self.native_pool,
            artwork=self._artwork.preview,
        )
        extension_service = ExtensionService(
            self.extensions, system, self.extension_pool, lambda: self._wake().set()
        )
        self.services = Services(
            configuration, state, system, extension_service, devices
        )
        self.lifecycle = Lifecycle(self)

    @property
    def extensions(self) -> ExtensionManager:
        return self._extensions

    @extensions.setter
    def extensions(self, manager: ExtensionManager) -> None:
        self._extensions = manager
        self.dispatcher.extensions = manager
        self.services.state.extensions = manager
        self.services.extensions.manager = manager

    @property
    def _config_mtime(self) -> float:
        if self.config_path is None:
            return 0.0
        try:
            return self.config_path.stat().st_mtime
        except OSError:
            return 0.0

    def _install_config(self, loaded: Config) -> None:
        self.console_config.install(loaded)

    async def reload_config_if_changed(self) -> bool:
        return await self.services.config.reload_if_changed()

    def client_summaries(self) -> list[dict[str, Any]]:
        return [
            {
                "id": client.id,
                "address": client.address,
                "device_id": client.device_id,
                "name": client.device_name,
            }
            for client in sorted(self.clients, key=lambda item: item.id)
            if client.authenticated
        ]

    async def _disconnect_device(self, device_id: str) -> None:
        matches = [client for client in self.clients if client.device_id == device_id]
        for client in matches:
            client.authenticated = False
        await asyncio.gather(
            *(client.close() for client in matches), return_exceptions=True
        )

    def local_addresses(self) -> list[str]:
        return list(self._addresses)

    def find_addresses(self) -> list[str]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("8.8.8.8", 80))
                return [f"{probe.getsockname()[0]}:{self.config.port}"]
        except OSError:
            return []

    def health(self) -> dict[str, Any]:
        components = {
            "tcp": "ready"
            if self._server and self._server.is_serving()
            else "starting",
            "discovery": "ready" if self._discovery_transport else "degraded",
            "http": ("ready" if self._ui and self._ui.running else "degraded")
            if self.ui_port is not None
            else "disabled",
            "collector": "ready" if self.last_collection_at else "idle",
            "extensions": "ready",
            "controls": "paused" if self.controls_paused else "ready",
        }
        status = (
            "stopping"
            if self._closing
            else ("degraded" if "degraded" in components.values() else "ready")
        )
        return {
            "status": status,
            "components": components,
            "uptime": time.monotonic() - self.started_at,
            "last_collection_age": None
            if self.last_collection_at is None
            else time.monotonic() - self.last_collection_at,
        }

    async def _poll_loop(self) -> None:
        try:
            await self._poll_forever()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.log(
                f"Collecte interrompue : {type(error).__name__}. Arret supervise de l'agent."
            )
            raise

    async def start(self) -> None:
        await self.lifecycle.start()

    def request_stop(self) -> None:
        self._stop.set()

    @property
    def controls_paused(self) -> bool:
        until = self._controls_paused_until
        return until is not None and (math.isinf(until) or until > time.monotonic())

    @property
    def controls_pause_remaining(self) -> int | None:
        until = self._controls_paused_until
        if until is None or math.isinf(until):
            return None
        return max(0, math.ceil(until - time.monotonic()))

    def pause_controls(self, seconds: int | None) -> None:
        """Reject console mutations while keeping discovery and the tray alive."""

        if seconds is not None and seconds <= 0:
            raise ValueError("Pause duration must be positive")
        self._controls_paused_until = (
            math.inf if seconds is None else time.monotonic() + seconds
        )
        self.event(
            "controls.paused",
            "Commandes 3DS suspendues"
            + ("" if seconds is None else f" pour {seconds // 60} min"),
        )

    def resume_controls(self) -> None:
        if self._controls_paused_until is None:
            return
        self._controls_paused_until = None
        self.event("controls.resumed", "Commandes 3DS reactivees")

    def expire_controls_pause(self) -> bool:
        until = self._controls_paused_until
        if until is None or math.isinf(until) or until > time.monotonic():
            return False
        self._controls_paused_until = None
        self.event("controls.resumed", "Commandes 3DS reactivees automatiquement")
        return True

    async def close(self) -> None:
        if self._close_task is None:
            self._close_task = asyncio.create_task(
                self.lifecycle.close(), name="agent-shutdown"
            )
        await asyncio.shield(self._close_task)

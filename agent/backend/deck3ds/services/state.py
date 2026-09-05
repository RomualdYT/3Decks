"""Read models for the editor: requests read memory, never collect OS state."""

from __future__ import annotations
import copy
import time
from collections.abc import Mapping
from typing import Any, Callable
from ..extensions.bridge import preview_payload, state_payload
from ..extensions.manager import ExtensionManager
from ..feature_catalog import FEATURE_SPECS
from ..pairing import PairingManager
from ..platforms.base import Platform
from .catalog import build_schema, effective_capabilities
from .configuration import ConfigService
from .executor import WorkPool


class StateService:
    def __init__(
        self,
        config: ConfigService,
        platform: Platform,
        extensions: ExtensionManager,
        pairing: PairingManager,
        version: str,
        snapshot: Callable[[], Mapping[str, Any]],
        clients: Callable[[], list[dict[str, Any]]],
        addresses: Callable[[], list[str]],
        logs: Callable[[], list[str]],
        events: Callable[[], list[dict[str, Any]]],
        counters: Callable[[], dict[str, int]],
        devices: Callable[[], list[dict[str, str]]],
        health: Callable[[], dict[str, Any]],
        controls: Callable[[], dict[str, Any]],
        pool: WorkPool,
    ) -> None:
        self.config, self.platform, self.extensions = config, platform, extensions
        self.pairing, self.version = pairing, version
        # Borrow the cached snapshot synchronously; read() detaches the complete
        # response once. Requiring an already-deep-copied snapshot doubles work.
        self._snapshot_view, self._clients, self._addresses = (
            snapshot,
            clients,
            addresses,
        )
        self._logs, self._events, self._counters = logs, events, counters
        self._devices, self.health, self._controls, self._pool = (
            devices,
            health,
            controls,
            pool,
        )
        self._capabilities = platform.capabilities()
        self._notifications: dict[str, object] = {
            "provider": "none",
            "available": False,
            "access": "unknown",
        }
        self._metadata_at = 0.0

    async def refresh_metadata(self) -> None:
        if time.monotonic() - self._metadata_at < 10.0:
            return
        self._capabilities = await self._pool.run(self.platform.capabilities)
        self._notifications = await self._pool.run(self.platform.notification_status)
        self._metadata_at = time.monotonic()

    def schema(self) -> dict[str, Any]:
        current = self.config.current
        schema = build_schema(
            self._capabilities,
            current.obs.enabled,
            current.features,
            self.platform.name,
        )
        catalog = self.extensions.catalog()
        schema["actions"].extend(catalog["actions"])
        schema["dashboards"].extend(catalog["dashboards"])
        schema["extension_sources"] = catalog["sources"]
        return schema

    def pairing_state(self) -> dict[str, Any]:
        return dict(self.pairing.snapshot(bool(self.config.current.token)))

    def rotate_pairing(self) -> dict[str, Any]:
        self.pairing.rotate()
        return self.pairing_state()

    def read(self) -> dict[str, Any]:
        current = self.config.current
        capabilities = effective_capabilities(self._capabilities, current.features)
        capabilities["obs"] = current.obs.enabled
        return copy.deepcopy(
            {
                "version": self.version,
                "config_revision": current.revision,
                "platform": self.platform.name,
                "listen": f"{current.host}:{current.port}",
                "hints": self._addresses(),
                "token_set": bool(current.token),
                "pairing": self.pairing_state(),
                "discovery_port": 38122,
                "clients": self._clients(),
                "paired_devices": self._devices(),
                "capabilities": capabilities,
                "features": {
                    key: getattr(current.features, key) for key in FEATURE_SPECS
                },
                "notifications": self._notifications,
                "snapshot": {
                    **self._snapshot_view(),
                    **state_payload(self.extensions, current),
                    **preview_payload(self.extensions),
                },
                "logs": self._logs(),
                "events": self._events(),
                "counters": self._counters(),
                **self._controls(),
            }
        )

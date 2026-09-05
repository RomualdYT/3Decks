"""Trusted extension operations; never accepts a browser-supplied file path."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
from ..extensions.manager import ExtensionManager
from ..extensions.manifest import ExtensionError
from ..platforms.base import ActionFailed, SelectionCancelled, Unsupported
from .errors import ServiceError
from .executor import WorkPool
from .system import SystemService


class ExtensionService:
    def __init__(
        self,
        manager: ExtensionManager,
        system: SystemService,
        pool: WorkPool,
        wake: Callable[[], None],
    ) -> None:
        self.manager = manager
        self.system = system
        self.pool = pool
        self.wake = wake

    async def describe(self) -> dict[str, Any]:
        return dict(await self.pool.run(self.manager.describe))

    async def manage(self, raw: dict[str, Any]) -> dict[str, Any]:
        operation, identifier = raw.get("operation"), raw.get("id", "")
        if not isinstance(identifier, str):
            raise ServiceError(422, "Invalid extension identifier", "invalid_extension")
        try:
            if operation == "install":
                selected = await self.system.pick("file")
                if selected["cancelled"]:
                    return {"cancelled": True}
                await self.pool.run(self.manager.install, Path(selected["path"]))
            elif operation == "rescan":
                await self.pool.run(self.manager.rescan)
            elif operation == "enable":
                if raw.get("trust") is not True or not isinstance(
                    raw.get("digest"), str
                ):
                    raise ExtensionError("Explicit package trust approval is required")
                await self.pool.run(
                    self.manager.enable, identifier, True, raw["digest"]
                )
            elif operation == "disable":
                await self.pool.run(self.manager.enable, identifier, False)
            elif operation == "configure":
                if not isinstance(raw.get("settings"), dict):
                    raise ExtensionError("Settings must be an object")
                await self.pool.run(self.manager.configure, identifier, raw["settings"])
            elif operation == "restart":
                await self.pool.run(self.manager.restart, identifier)
            elif operation == "remove":
                if raw.get("confirm") is not True:
                    raise ExtensionError("Confirm removal first")
                await self.pool.run(self.manager.remove, identifier)
            else:
                raise ExtensionError("Unknown extension operation")
        except SelectionCancelled:
            return {"cancelled": True}
        except (ExtensionError, Unsupported, ActionFailed, OSError) as error:
            raise ServiceError(422, str(error), "extension_operation_failed") from error
        self.wake()
        return {"ok": True}

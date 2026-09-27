"""Explicit user operations on native integrations, isolated from collection."""

from __future__ import annotations
from typing import Any
from .. import config
from ..obs import ObsError, test_connection
from ..platforms.base import ActionFailed, Platform, SelectionCancelled, Unsupported
from .errors import ServiceError
from .executor import WorkPool


class SystemService:
    def __init__(
        self, platform: Platform, operations: WorkPool, dialogs: WorkPool
    ) -> None:
        self.platform = platform
        self.operations = operations
        self.dialogs = dialogs

    async def apps(self) -> dict[str, Any]:
        return {"apps": await self.operations.run(self.platform.list_launchable_apps)}

    async def pick(self, kind: str) -> dict[str, Any]:
        if kind not in ("file", "folder"):
            raise ServiceError(422, "type de selection invalide", "invalid_selection")
        try:
            path = await self.dialogs.run(self.platform.choose_path, kind)
        except SelectionCancelled:
            return {"cancelled": True, "path": "", "kind": kind}
        except (Unsupported, ActionFailed) as error:
            raise ServiceError(409, str(error), "selection_unavailable") from error
        return {"cancelled": False, "path": path, "kind": kind}

    async def permission(self, permission: str) -> dict[str, Any]:
        if not permission:
            raise ServiceError(422, "autorisation manquante", "invalid_permission")
        try:
            await self.operations.run(
                self.platform.open_permission_settings, permission
            )
        except (Unsupported, ActionFailed) as error:
            raise ServiceError(409, str(error), "permission_unavailable") from error
        return {"opened": True, "permission": permission}

    async def obs(self, raw: object) -> dict[str, Any]:
        try:
            settings = config.parse_obs(raw)
        except config.ConfigError as error:
            raise ServiceError(422, str(error), "invalid_obs_config") from error
        try:
            status = await self.operations.run(test_connection, settings)
        except ObsError as error:
            raise ServiceError(409, str(error), "obs_unavailable") from error
        return dict(status.as_payload())

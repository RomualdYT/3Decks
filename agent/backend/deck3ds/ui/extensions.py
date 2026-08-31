"""Authenticated local extension management. Native file selection only."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ..extensions.manifest import ExtensionError
from ..platforms.base import ActionFailed, SelectionCancelled, Unsupported
from .http import HttpError, Request, Response


class ExtensionApi:
    async def get_extensions(self, request: Request) -> Response:
        return Response.json(await asyncio.to_thread(self.server.extensions.describe))

    async def manage_extension(self, request: Request) -> Response:
        raw = request.json()
        if not isinstance(raw, dict):
            raise HttpError(422, "Extension operation must be an object")
        operation = raw.get("operation")
        identifier = raw.get("id", "")
        if not isinstance(identifier, str):
            raise HttpError(422, "Invalid extension identifier")
        manager = self.server.extensions
        try:
            if operation == "install":
                # The browser cannot name an executable/path. A native file
                # dialog requires a deliberate local user selection.
                selected = await asyncio.to_thread(
                    self.server.platform.choose_path, "file"
                )
                await asyncio.to_thread(manager.install, Path(selected))
            elif operation == "rescan":
                await asyncio.to_thread(manager.rescan)
            elif operation == "enable":
                if raw.get("trust") is not True or not isinstance(
                    raw.get("digest"), str
                ):
                    raise ExtensionError("Explicit package trust approval is required")
                await asyncio.to_thread(manager.enable, identifier, True, raw["digest"])
            elif operation == "disable":
                await asyncio.to_thread(manager.enable, identifier, False)
            elif operation == "configure":
                if not isinstance(raw.get("settings"), dict):
                    raise ExtensionError("Settings must be an object")
                await asyncio.to_thread(manager.configure, identifier, raw["settings"])
            elif operation == "restart":
                await asyncio.to_thread(manager.restart, identifier)
            elif operation == "remove":
                if raw.get("confirm") is not True:
                    raise ExtensionError("Confirm removal first")
                await asyncio.to_thread(manager.remove, identifier)
            else:
                raise ExtensionError("Unknown extension operation")
        except SelectionCancelled:
            return Response.json({"cancelled": True})
        except (ExtensionError, Unsupported, ActionFailed, OSError) as error:
            raise HttpError(422, str(error)) from error
        self.server._wake().set()
        return Response.json({"ok": True})

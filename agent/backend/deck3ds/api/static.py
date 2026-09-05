"""Static assets with containment checks and fingerprint-only immutable caching."""

from __future__ import annotations
import re
from pathlib import Path
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class FrontendFiles(StaticFiles):
    def __init__(self, directory: Path) -> None:
        super().__init__(
            directory=directory, html=True, check_dir=False, follow_symlink=False
        )
        self.root = directory.resolve()

    async def get_response(self, path: str, scope: Scope) -> Response:
        # Starlette normalizes paths; inspect the ASGI decoded path as well.
        if ".." in scope["path"].replace("\\", "/").split("/"):
            raise HTTPException(403, "chemin refuse")
        target = (self.root / path).resolve()
        if target != self.root and self.root not in target.parents:
            raise HTTPException(403, "chemin refuse")
        response = await super().get_response(path, scope)
        if path.startswith("assets/") and re.search(
            r"-[A-Za-z0-9_-]{8,}\.(?:js|css|woff2?|png|svg)$", path
        ):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-store"
        return response

"""Pure FastAPI factory. No platform, socket, thread or extension is started here."""

from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Callable, cast
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from ..services.bundle import Services
from ..services.errors import ServiceError
from ..version import VERSION
from .models import ErrorResponse
from .routes import configuration, extensions, system
from .security import HttpSettings, LocalSecurity
from .static import FrontendFiles
from .input_models import input_schemas


async def openapi_document(request: Request) -> dict[str, Any]:
    # Stable endpoint callables: FastAPI caches their classification. A closure
    # capturing the app would retain its services across factory/start cycles.
    return cast(dict[str, Any], request.app.openapi())


async def api_not_found(request: Request, path: str) -> None:
    known = f"/api/{path}" in request.app.state.api_paths
    raise HTTPException(
        405 if known else 404, "methode refusee" if known else "route inconnue"
    )


class LocalApi(FastAPI):
    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is not None:
            return self.openapi_schema
        schema = super().openapi()
        schema.setdefault("components", {}).setdefault("schemas", {}).update(
            input_schemas()
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})[
            "LocalSession"
        ] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-Deck3DS-Token",
            "description": "Per-start local UI session; never the durable console pairing token.",
        }
        schema["security"] = [{"LocalSession": []}]
        return schema


def create_app(
    services: Services | None = None,
    settings: HttpSettings | None = None,
    static_root: Path | None = None,
    log: Callable[[str], None] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # HTTP owns no core resources. AgentRuntime is also usable without HTTP.
        app.state.http_ready = True
        try:
            yield
        finally:
            app.state.http_ready = False

    app = LocalApi(
        title="3Decks local agent API",
        version=VERSION,
        description="Authenticated loopback API. Console TCP and extension stdio protocols remain independent.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
        lifespan=lifespan,
    )
    app.state.services = services
    app.state.http_ready = False
    app.add_middleware(
        LocalSecurity, settings=settings or HttpSettings(), log=log or (lambda _: None)
    )
    errors: dict[int | str, dict[str, Any]] = {
        status: {"model": ErrorResponse, "description": description}
        for status, description in (
            (400, "Malformed body"),
            (403, "Local session refused"),
            (404, "Not found"),
            (405, "Method not allowed"),
            (409, "Conflict or unavailable integration"),
            (413, "Request too large"),
            (422, "Validation failed"),
            (500, "Internal error"),
            (503, "Agent unavailable"),
        )
    }
    for router in (configuration.router, system.router, extensions.router):
        app.include_router(router, prefix="/api", responses=errors)

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, error: ServiceError) -> JSONResponse:
        return JSONResponse(
            {
                "error": error.message,
                "code": error.code,
                "request_id": request.state.request_id,
            },
            status_code=error.status,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        invalid_json = any(item["type"] == "json_invalid" for item in error.errors())
        empty = not await request.body()
        return JSONResponse(
            {
                "error": "JSON invalide ou corps vide"
                if invalid_json or empty
                else "Champs de requete invalides",
                "code": "invalid_body"
                if invalid_json or empty
                else "validation_failed",
                "request_id": request.state.request_id,
            },
            status_code=400 if invalid_json or empty else 422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return JSONResponse(
            {
                "error": str(error.detail),
                "code": f"http_{error.status_code}",
                "request_id": request.state.request_id,
            },
            status_code=error.status_code,
            headers=error.headers,
        )

    app.add_api_route(
        "/api/openapi.json", openapi_document, methods=["GET"], include_in_schema=False
    )
    app.state.api_paths = {
        "/api" + route.path
        for router in (configuration.router, system.router, extensions.router)
        for route in router.routes
        if hasattr(route, "path")
    } | {"/api/openapi.json"}

    app.add_api_route(
        "/api/{path:path}",
        api_not_found,
        methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    app.mount("/", FrontendFiles(static_root or Path(__file__).parent / "static"))
    return app

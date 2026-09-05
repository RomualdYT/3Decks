"""Typed request dependency: never expose the runtime to a route."""

from typing import Annotated, cast
from fastapi import Depends, Request
from ..services.bundle import Services
from ..services.errors import ServiceError


async def services(request: Request) -> Services:
    result = getattr(request.app.state, "services", None)
    if result is None:
        raise ServiceError(503, "Agent indisponible", "not_ready")
    return cast(Services, result)


ApplicationServices = Annotated[Services, Depends(services)]

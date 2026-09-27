from typing import Any
from fastapi import APIRouter, Body
from ..catalog_models import Catalog
from ..dependencies import ApplicationServices
from ..input_models import request_schema
from ..models import ConfigRead, ConfigSaved, ValidationResult, JsonBody

router = APIRouter(tags=["configuration"])


@router.get(
    "/schema",
    response_model=Catalog,
    response_model_exclude_unset=True,
    operation_id="get_catalog",
)
async def schema(services: ApplicationServices) -> dict[str, Any]:
    return services.state.schema()


@router.get(
    "/config",
    response_model=ConfigRead,
    response_model_exclude_unset=True,
    operation_id="get_config",
)
async def read(services: ApplicationServices) -> dict[str, Any]:
    return services.config.document()


@router.put(
    "/config",
    response_model=ConfigSaved,
    response_model_exclude_unset=True,
    operation_id="save_config",
    openapi_extra=request_schema("ConfigInput"),
)
async def save(
    services: ApplicationServices, body: JsonBody = Body()
) -> dict[str, Any]:
    return await services.config.save(body.root)


@router.post(
    "/config/validate", response_model=ValidationResult, operation_id="validate_config"
)
async def validate(
    services: ApplicationServices, body: JsonBody = Body()
) -> dict[str, Any]:
    return services.config.validate(body.root)

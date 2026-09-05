from typing import Any
from fastapi import APIRouter
from ..catalog_models import ExtensionCatalog, ExtensionOperation, OperationResult
from ..dependencies import ApplicationServices

router = APIRouter(tags=["extensions"])


@router.get(
    "/extensions",
    response_model=ExtensionCatalog,
    response_model_exclude_unset=True,
    operation_id="get_extensions",
)
async def extensions(services: ApplicationServices) -> dict[str, Any]:
    return await services.extensions.describe()


@router.post(
    "/extensions",
    response_model=OperationResult,
    response_model_exclude_unset=True,
    operation_id="manage_extension",
)
async def manage(
    body: ExtensionOperation, services: ApplicationServices
) -> dict[str, Any]:
    return await services.extensions.manage(body.model_dump())

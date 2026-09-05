from typing import Any
from fastapi import APIRouter, Body
from ..dependencies import ApplicationServices
from ..models import (
    AgentState,
    Apps,
    DeviceRevoked,
    Health,
    ObsStatus,
    PairingState,
    PathRequest,
    PathSelection,
    PermissionOpened,
    PermissionRequest,
)
from ..models import JsonBody
from ..input_models import request_schema

router = APIRouter(tags=["system"])


@router.get(
    "/state",
    response_model=AgentState,
    response_model_exclude_unset=True,
    operation_id="get_state",
)
async def state(services: ApplicationServices) -> dict[str, Any]:
    return services.state.read()


@router.get("/health", response_model=Health, operation_id="get_health")
async def health(services: ApplicationServices) -> dict[str, Any]:
    return services.state.health()


@router.get("/apps", response_model=Apps, operation_id="get_apps")
async def apps(services: ApplicationServices) -> dict[str, Any]:
    return await services.system.apps()


@router.post("/paths/pick", response_model=PathSelection, operation_id="pick_path")
async def pick(body: PathRequest, services: ApplicationServices) -> dict[str, Any]:
    return await services.system.pick(body.kind)


@router.post(
    "/permissions/open", response_model=PermissionOpened, operation_id="open_permission"
)
async def permission(
    body: PermissionRequest, services: ApplicationServices
) -> dict[str, Any]:
    return await services.system.permission(body.permission)


@router.post(
    "/obs/test",
    response_model=ObsStatus,
    response_model_exclude_unset=True,
    operation_id="test_obs",
    openapi_extra=request_schema("ObsInput"),
)
async def obs(services: ApplicationServices, body: JsonBody = Body()) -> dict[str, Any]:
    return await services.system.obs(body.root)


@router.post(
    "/pairing/rotate", response_model=PairingState, operation_id="rotate_pairing"
)
async def pairing(services: ApplicationServices) -> dict[str, Any]:
    return services.state.rotate_pairing()


@router.delete(
    "/paired-devices/{device_id}",
    response_model=DeviceRevoked,
    operation_id="revoke_paired_device",
)
async def revoke_device(
    device_id: str, services: ApplicationServices
) -> dict[str, bool]:
    return await services.devices.revoke(device_id)

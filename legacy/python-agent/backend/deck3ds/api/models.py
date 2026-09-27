"""HTTP wire models. Business validation remains in configuration/ and services/."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue, RootModel

Locale = Literal["en", "fr"]
Localized = str | dict[Locale, str]


class JsonBody(RootModel[JsonValue]):
    """Keep JSON recursive references scoped to a Pydantic model."""


class WireModel(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)


class ActionDocument(WireModel):
    type: str


class ButtonDocument(WireModel):
    id: str
    slot: int
    label: Localized
    icon: str
    color: str
    action: str | ActionDocument
    toggle: str = ""
    hold_label: Localized = ""
    hold_action: str | ActionDocument | None = None


class PageDocument(WireModel):
    id: str
    title: Localized
    icon: str
    dashboard: str
    buttons: list[ButtonDocument]
    layout: Literal["grid", "list"] = "grid"
    source: str = ""


class ServerSettings(WireModel):
    host: str
    port: int
    token: str
    poll_interval: float
    volume_step: int


class ObsSettings(WireModel):
    enabled: bool
    host: str
    port: int
    password: str
    timeout: float


class Integrations(WireModel):
    obs: ObsSettings


class ConfigDocument(WireModel):
    revision: int
    server: ServerSettings
    features: dict[str, bool]
    integrations: Integrations
    pages: list[PageDocument]
    scripts: dict[str, list[str]] = Field(default_factory=dict)


class ConfigRead(WireModel):
    config: ConfigDocument
    path: str


class ConfigSaved(WireModel):
    saved: bool
    config: ConfigDocument


class ValidationResult(WireModel):
    valid: bool
    error: str


class ErrorResponse(BaseModel):
    error: str
    code: str
    request_id: str


class PairingState(WireModel):
    required: bool
    code: str
    expires_in: int


class ClientSummary(WireModel):
    id: int
    address: str
    device_id: str = ""
    name: str = ""


class PairedDevice(WireModel):
    id: str
    name: str
    created_at: str
    last_seen: str


class DeviceRevoked(WireModel):
    revoked: bool


class RuntimeEvent(WireModel):
    timestamp: str
    name: str
    level: Literal["debug", "info", "warning", "error"]
    message: str
    fields: dict[str, JsonValue]


class NotificationStatus(WireModel):
    access: str = "unknown"
    enabled: bool = True
    available: bool = False
    error: str = ""
    settings_action: str = ""


class AgentState(WireModel):
    version: str
    config_revision: int
    platform: str
    listen: str
    hints: list[str]
    token_set: bool
    pairing: PairingState
    discovery_port: int
    clients: list[ClientSummary]
    paired_devices: list[PairedDevice]
    capabilities: dict[str, bool]
    features: dict[str, bool]
    notifications: NotificationStatus
    snapshot: dict[str, JsonValue]
    logs: list[str]
    events: list[RuntimeEvent]
    counters: dict[str, int]
    paused: bool
    pause_remaining: int | None


class Health(WireModel):
    status: Literal["ready", "degraded", "stopping"]
    components: dict[str, str]
    uptime: float
    last_collection_age: float | None


class Apps(WireModel):
    apps: list[str]


class PathRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    kind: Literal["file", "folder"]


class PathSelection(WireModel):
    cancelled: bool
    path: str
    kind: Literal["file", "folder"]


class PermissionRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    permission: str


class PermissionOpened(WireModel):
    opened: bool
    permission: str


class ObsStatus(WireModel):
    connected: bool
    obs_version: str = ""
    current_scene: str = ""
    scenes: list[str] = Field(default_factory=list)

"""Stable catalog shapes with dynamic, namespaced extension contributions."""

from __future__ import annotations
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from .models import Localized, WireModel


class Translations(WireModel):
    en: str
    fr: str


class Choice(WireModel):
    value: str
    label: Localized


class ActionArgument(WireModel):
    name: str
    type: Literal[
        "text", "number", "hotkey", "page", "script", "password", "boolean", "select"
    ]
    required: bool
    label: Localized = ""
    description: Localized = ""
    default: str | int | float | bool | None = None
    min: float | None = None
    max: float | None = None
    max_length: int | None = None
    choices: list[Choice] = Field(default_factory=list)


class ActionSpec(WireModel):
    kind: str
    category: str
    icon: str
    color: str
    title: Translations
    description: Translations
    arguments: list[ActionArgument]
    supported: bool
    capability: str | None
    extension: str = ""
    extension_name: Localized = ""


class FeatureSpec(WireModel):
    key: str
    title: Translations
    description: Translations
    parent: str | None
    platforms: list[str]
    enabled: bool
    available: bool


class KeyDescription(WireModel):
    name: str
    label_en: str
    label_fr: str


class Key(KeyDescription):
    group: str


class Keys(WireModel):
    modifiers: list[KeyDescription]
    groups: list[str]
    keys: list[Key]


class Dashboard(WireModel):
    name: str
    supported: bool
    title: Localized = ""
    description: Localized = ""
    icon: str = ""


class Limits(BaseModel):
    model_config = ConfigDict(extra="allow")
    __pydantic_extra__: dict[str, float | list[float]] = Field(init=False)
    pages: int
    buttons_per_page: int
    label: int
    id: int


class Catalog(WireModel):
    actions: list[ActionSpec]
    features: list[FeatureSpec]
    icons: list[str]
    keys: Keys
    dashboards: list[Dashboard]
    extension_sources: list[Dashboard]
    locales: list[str]
    layouts: list[str]
    sources: list[str]
    capabilities: dict[str, bool]
    limits: Limits
    defaults: dict[str, str | int | float]


class Contribution(WireModel):
    id: str
    title: Localized
    description: Localized


class ExtensionManifest(WireModel):
    api_version: int
    id: str
    version: str
    name: Localized
    description: Localized
    author: str
    platforms: list[str]
    permissions: list[str]
    settings: list[ActionArgument]
    actions: list[Contribution]
    sources: list[Contribution]
    dashboards: list[Contribution]


class InstalledExtension(WireModel):
    manifest: ExtensionManifest
    digest: str
    enabled: bool
    status: str
    error: str
    updated_at: float
    settings: dict[str, JsonValue]
    secret_fields_set: list[str]


class ExtensionCatalog(WireModel):
    api_version: int
    directory: str
    extensions: list[InstalledExtension]
    errors: list[str]


class Operation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Install(Operation):
    operation: Literal["install", "rescan"]


class TargetOperation(Operation):
    operation: Literal["disable", "restart"]
    id: str


class Enable(Operation):
    operation: Literal["enable"]
    id: str
    trust: bool
    digest: str


class Configure(Operation):
    operation: Literal["configure"]
    id: str
    settings: dict[str, JsonValue]


class Remove(Operation):
    operation: Literal["remove"]
    id: str
    confirm: bool


ExtensionOperation = Annotated[
    Install | TargetOperation | Enable | Configure | Remove,
    Field(discriminator="operation"),
]


class OperationResult(WireModel):
    ok: bool = False
    cancelled: bool = False

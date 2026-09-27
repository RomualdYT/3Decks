"""Abbreviated input contracts; defaults and rules remain in the domain parser.

Routes receive raw JSON so validation can return valid:false without coercion.
Pydantic exports these structural contracts into OpenAPI, without instantiating
them on the write path or losing unknown, namespaced action arguments.
"""

from typing import Annotated, Literal, NotRequired, TypedDict
from pydantic import Field, TypeAdapter
from .models import ActionDocument, Localized


class ServerInput(TypedDict, total=False):
    host: str
    port: int
    token: str
    poll_interval: float
    volume_step: int


class ObsInput(TypedDict, total=False):
    enabled: bool
    host: str
    port: int
    password: str
    timeout: float


class IntegrationsInput(TypedDict, total=False):
    obs: ObsInput


class ButtonInput(TypedDict):
    id: str
    slot: NotRequired[int]
    label: NotRequired[Localized]
    icon: NotRequired[str]
    color: NotRequired[str]
    action: NotRequired[str | ActionDocument]
    toggle: NotRequired[str]
    hold_action: NotRequired[str | ActionDocument]
    hold_label: NotRequired[Localized]


class PageInput(TypedDict):
    id: str
    title: NotRequired[Localized]
    icon: NotRequired[str]
    dashboard: NotRequired[str]
    layout: NotRequired[Literal["grid", "list"]]
    source: NotRequired[str]
    buttons: NotRequired[list[ButtonInput]]


class ConfigInput(TypedDict):
    pages: list[PageInput]
    revision: NotRequired[int]
    server: NotRequired[ServerInput]
    integrations: NotRequired[IntegrationsInput]
    features: NotRequired[dict[str, bool]]
    scripts: NotRequired[
        Annotated[dict[str, list[str]], Field(json_schema_extra={"readOnly": True})]
    ]


def input_schemas() -> dict[str, object]:
    definitions: dict[str, object] = {}
    for name, adapter in (
        ("ConfigInput", TypeAdapter(ConfigInput)),
        ("ObsInput", TypeAdapter(ObsInput)),
    ):
        document = adapter.json_schema(ref_template="#/components/schemas/{model}")
        definitions.update(document.pop("$defs", {}))
        definitions[name] = document
    return definitions


def request_schema(name: str) -> dict[str, object]:
    return {
        "requestBody": {
            "content": {
                "application/json": {"schema": {"$ref": f"#/components/schemas/{name}"}}
            }
        }
    }

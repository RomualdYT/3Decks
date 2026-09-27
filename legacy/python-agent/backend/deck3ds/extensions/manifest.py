"""Declarative, bounded extension contracts shared by the UI and runtime."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from ..icon_catalog import ICONS

ID = re.compile(r"[a-z][a-z0-9.-]{2,47}\Z")
KEY = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
REFERENCE = re.compile(r"ext:([a-z][a-z0-9.-]{2,47})/([a-z][a-z0-9_-]{0,31})\Z")
MAX_MESSAGE = 64 * 1024
PERMISSIONS = {"network", "filesystem", "system", "notifications"}


class ExtensionError(Exception):
    """A user-facing extension error, not an agent failure."""


def reference(value: object) -> tuple[str, str] | None:
    match = REFERENCE.fullmatch(value) if isinstance(value, str) else None
    return (match[1], match[2]) if match else None


def localized(value: object, locale: str = "en") -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get(locale) or value.get("en") or "")
    return ""


def text(value: object, context: str, limit: int = 180) -> dict[str, str]:
    if isinstance(value, str):
        value = {"en": value, "fr": value}
    if not isinstance(value, dict) or not isinstance(value.get("en"), str):
        raise ExtensionError(f"{context}: English text (en) is required")
    result = {}
    for locale in ("en", "fr"):
        item = value.get(locale, value["en"])
        if not isinstance(item, str) or not item.strip() or len(item) > limit:
            raise ExtensionError(f"{context}: text must contain 1–{limit} characters")
        result[locale] = item.strip()
    return result


def fields(raw: object, context: str) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) > 16:
        raise ExtensionError(f"{context}: maximum 16 fields")
    result = []
    names = set()
    for item in raw:
        if not isinstance(item, dict) or not KEY.fullmatch(str(item.get("name", ""))):
            raise ExtensionError(f"{context}: invalid field name")
        name = item["name"]
        kind = item.get("type", "text")
        if (
            name in names
            or not isinstance(kind, str)
            or kind
            not in {
                "text",
                "password",
                "number",
                "boolean",
                "select",
            }
        ):
            raise ExtensionError(
                f"{context}.{name}: duplicate name or unsupported type"
            )
        names.add(name)
        field = dict(item)
        field.update(name=name, type=kind, label=text(item.get("label", name), context))
        field["required"] = item.get("required", False)
        if not isinstance(field["required"], bool):
            raise ExtensionError(f"{context}.{name}: required must be boolean")
        if "description" in item:
            field["description"] = text(item["description"], context, 300)
        for bound in ("min", "max"):
            if bound in item and (
                type(item[bound]) not in (int, float) or not math.isfinite(item[bound])
            ):
                raise ExtensionError(f"{context}.{name}: invalid {bound}")
        if item.get("min", -float("inf")) > item.get("max", float("inf")):
            raise ExtensionError(f"{context}.{name}: min exceeds max")
        if kind == "select":
            choices = item.get("choices")
            if not isinstance(choices, list) or not 1 <= len(choices) <= 32:
                raise ExtensionError(f"{context}.{name}: select needs 1–32 choices")
            seen = set()
            normalized = []
            for choice in choices:
                if not isinstance(choice, dict) or not isinstance(
                    choice.get("value"), str
                ):
                    raise ExtensionError(f"{context}.{name}: invalid choice")
                key = choice["value"]
                if not key or len(key) > 64 or key in seen:
                    raise ExtensionError(
                        f"{context}.{name}: invalid or duplicate choice"
                    )
                seen.add(key)
                normalized.append(
                    {"value": key, "label": text(choice.get("label", key), context)}
                )
            field["choices"] = normalized
        if "default" in field:
            if kind == "password":
                raise ExtensionError(
                    f"{context}.{name}: secrets must not have manifest defaults"
                )
            validate_values([dict(field, required=False)], {name: field["default"]})
        result.append(field)
    return result


def validate_values(specs: list[dict], values: object) -> dict[str, Any]:
    if not isinstance(values, dict):
        raise ExtensionError("Parameters must be an object")
    unknown = set(values) - {item["name"] for item in specs}
    if unknown:
        raise ExtensionError(f"Unknown parameters: {', '.join(sorted(unknown))}")
    result = {}
    for spec in specs:
        name = spec["name"]
        value = values.get(name, spec.get("default"))
        if value is None and "default" in spec:
            value = spec["default"]
        if value is None or (value == "" and spec["type"] != "boolean"):
            if spec.get("required"):
                raise ExtensionError(f"{name}: value required")
            if value is not None:
                result[name] = value
            continue
        kind = spec["type"]
        if kind == "boolean":
            valid = isinstance(value, bool)
        elif kind == "number":
            valid = type(value) in (int, float) and math.isfinite(value)
            valid = valid and spec.get("min", -float("inf")) <= value <= spec.get(
                "max", float("inf")
            )
        else:
            valid = isinstance(value, str) and len(value) <= 2048
            if kind == "select":
                valid = valid and value in {
                    choice["value"] for choice in spec["choices"]
                }
        if not valid:
            raise ExtensionError(f"{name}: invalid {kind} value")
        result[name] = value
    return result


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size > MAX_MESSAGE:
            raise ExtensionError("Manifest exceeds 64 KiB")
        raw = json.loads(path.read_text(encoding="utf-8"))
        # Reject non-finite numbers and lone Unicode surrogates before any
        # catalogue/API can serialize an untrusted manifest.
        json.dumps(raw, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (OSError, ValueError) as error:
        raise ExtensionError("Cannot read extension.json") from error
    if (
        not isinstance(raw, dict)
        or type(raw.get("api_version")) is not int
        or raw["api_version"] != 1
    ):
        raise ExtensionError("Unsupported extension API; expected api_version: 1")
    if not ID.fullmatch(str(raw.get("id", ""))):
        raise ExtensionError(
            "Invalid extension id (lowercase reverse-domain recommended)"
        )
    if not re.fullmatch(
        r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", str(raw.get("version", ""))
    ):
        raise ExtensionError("version must use major.minor.patch")
    manifest = dict(raw)
    manifest["name"] = text(raw.get("name"), "name", 64)
    manifest["description"] = text(raw.get("description"), "description", 300)
    if not isinstance(raw.get("author"), str) or not 1 <= len(raw["author"]) <= 100:
        raise ExtensionError("author is required (maximum 100 characters)")
    platforms = raw.get("platforms", ["darwin", "win32", "linux"])
    if (
        not isinstance(platforms, list)
        or not platforms
        or any(item not in ("darwin", "win32", "linux") for item in platforms)
    ):
        raise ExtensionError("platforms must list darwin, win32 and/or linux")
    manifest["platforms"] = platforms
    permissions = raw.get("permissions", [])
    if not isinstance(permissions, list) or any(
        not isinstance(item, str) or item not in PERMISSIONS for item in permissions
    ):
        raise ExtensionError("Unknown permission declaration")
    manifest["permissions"] = sorted(set(permissions))
    runtime = raw.get("runtime", "python")
    if runtime == "python":
        entry = raw.get("entrypoint", "main.py")
        if (
            not isinstance(entry, str)
            or Path(entry).is_absolute()
            or ".." in Path(entry).parts
            or "\\" in entry
        ):
            raise ExtensionError("entrypoint must be a relative package path")
        if not (path.parent / entry).is_file():
            raise ExtensionError("Python entrypoint not found")
        manifest["entrypoint"] = entry
    elif runtime == "command":
        command = raw.get("command")
        if (
            not isinstance(command, list)
            or not 1 <= len(command) <= 16
            or any(
                not isinstance(arg, str) or not arg or len(arg) > 512 for arg in command
            )
        ):
            raise ExtensionError("command must be a non-empty argv array (no shell)")
    else:
        raise ExtensionError("runtime must be python or command")
    manifest["runtime"] = runtime
    interval = raw.get("poll_interval", 2)
    if type(interval) not in (int, float) or not 0.5 <= interval <= 60:
        raise ExtensionError("poll_interval must be between 0.5 and 60 seconds")
    manifest["poll_interval"] = interval
    manifest["settings"] = fields(raw.get("settings", []), "settings")
    for group, maximum in (("actions", 32), ("sources", 8), ("dashboards", 8)):
        items = raw.get(group, [])
        if not isinstance(items, list) or len(items) > maximum:
            raise ExtensionError(f"{group}: maximum {maximum} contributions")
        normalized = []
        seen = set()
        for item in items:
            if (
                not isinstance(item, dict)
                or not KEY.fullmatch(str(item.get("id", "")))
                or item["id"] in seen
            ):
                raise ExtensionError(f"{group}: invalid or duplicate id")
            seen.add(item["id"])
            entry = dict(item)
            entry["title"] = text(item.get("title"), group, 64)
            entry["description"] = text(
                item.get("description", item["title"]), group, 300
            )
            entry["icon"] = item.get("icon", "app")
            entry["color"] = item.get("color", "#66CB10")
            if (
                not isinstance(entry["icon"], str)
                or len(entry["icon"]) > 16
                or not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(entry["color"]))
            ):
                raise ExtensionError(f"{group}: invalid icon or #RRGGBB color")
            if entry["icon"] not in ICONS:
                entry["icon"] = "app"
            if group == "actions":
                entry["arguments"] = fields(item.get("arguments", []), group)
                if any(field["name"] == "type" for field in entry["arguments"]):
                    raise ExtensionError(
                        "Argument name 'type' is reserved by the action protocol"
                    )
                if "state" in item and not KEY.fullmatch(str(item["state"])):
                    raise ExtensionError("action.state: invalid key")
            normalized.append(entry)
        manifest[group] = normalized
    return manifest

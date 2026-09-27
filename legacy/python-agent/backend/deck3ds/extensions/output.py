"""Validate extension-produced UI data before it can reach a console."""

from __future__ import annotations

import re

from ..icon_catalog import ICONS

from .manifest import ExtensionError, KEY, text, validate_values


def short(value: object, limit: int) -> str:
    if not isinstance(value, str):
        raise ExtensionError("UI values must be strings")
    # Console buffers count UTF-8 bytes, not Python characters.
    return value.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def normalize(manifest: dict, raw: object) -> dict:
    if not isinstance(raw, dict):
        raise ExtensionError("poll must return an object")
    states = raw.get("states", {})
    if (
        not isinstance(states, dict)
        or len(states) > 32
        or any(
            not isinstance(key, str)
            or not KEY.fullmatch(key)
            or not isinstance(value, bool)
            for key, value in states.items()
        )
    ):
        raise ExtensionError("states must contain at most 32 boolean entries")
    result = {"states": dict(states), "dashboards": {}, "sources": {}}
    for group in ("dashboards", "sources"):
        values = raw.get(group, {})
        if not isinstance(values, dict) or set(values) - {
            item["id"] for item in manifest[group]
        }:
            raise ExtensionError(f"Undeclared {group} contribution")
        for key, value in values.items():
            if group == "dashboards":
                result[group][key] = panel(value)
            else:
                result[group][key] = entries(manifest, value)
    return result


def panel(raw: object) -> dict:
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("cards", []), list)
        or len(raw.get("cards", [])) > 4
    ):
        raise ExtensionError("A dashboard supports at most four cards")
    cards = []
    for item in raw.get("cards", []):
        if not isinstance(item, dict):
            raise ExtensionError("Dashboard cards must be objects")
        card = {
            "label": text(item.get("label", "Info"), "card label", 48),
            "value": short(item.get("value", ""), 40),
            "detail": text(item.get("detail") or " ", "card detail", 80)
            if item.get("detail")
            else {"en": "", "fr": ""},
        }
        if "progress" in item:
            value = item["progress"]
            if type(value) not in (int, float) or not 0 <= value <= 100:
                raise ExtensionError("Card progress must be between 0 and 100")
            card["progress"] = int(value)
        cards.append(card)
    status = raw.get("status", "neutral")
    if status not in ("neutral", "ok", "warning", "error"):
        raise ExtensionError("Unknown dashboard status")
    return {
        "title": text(raw.get("title", "Extension"), "dashboard title", 64),
        "status": status,
        "cards": cards,
    }


def entries(manifest: dict, raw: object) -> list[dict]:
    if not isinstance(raw, list) or len(raw) > 32:
        raise ExtensionError("A source supports at most 32 entries")
    result = []
    seen = set()
    actions = {item["id"]: item for item in manifest["actions"]}
    for item in raw:
        if (
            not isinstance(item, dict)
            or not KEY.fullmatch(str(item.get("id", "")))
            or item["id"] in seen
        ):
            raise ExtensionError("Invalid or duplicate source entry id")
        seen.add(item["id"])
        action = item.get("action", {})
        if not isinstance(action, dict) or action.get("id") not in actions:
            raise ExtensionError("Source entry must refer to a declared action")
        arguments = validate_values(
            actions[action["id"]]["arguments"], action.get("arguments", {})
        )
        color = item.get("color", "#66CB10")
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ExtensionError("Invalid entry color")
        if "active" in item and not isinstance(item["active"], bool):
            raise ExtensionError("Entry active must be boolean")
        result.append(
            {
                "id": item["id"],
                "label": text(item.get("label", item["id"]), "entry label", 64),
                "detail": text(item["detail"], "entry detail", 80)
                if item.get("detail")
                else {"en": "", "fr": ""},
                "icon": item.get("icon", "app") if item.get("icon") in ICONS else "app",
                "color": color,
                "active": item.get("active", False),
                "action": {"id": action["id"], "arguments": arguments},
            }
        )
    return result


def localize(value: object, locale: str) -> object:
    """Translate only the declarative extension subtree, never native state."""
    if isinstance(value, dict):
        if "en" in value and set(value) <= {"en", "fr"}:
            return value.get(locale, value["en"])
        return {key: localize(item, locale) for key, item in value.items()}
    if isinstance(value, list):
        return [localize(item, locale) for item in value]
    return value

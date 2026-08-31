"""Translate cached extension contributions into the existing console model."""

from __future__ import annotations

import json

from ..config import Action, ButtonConfig, ListEntry
from .manifest import reference
from .output import localize, short


def source_entries(manager, source: str, locale: str = "en") -> list[dict]:
    target = reference(source)
    if target is None:
        return []
    item = manager.items.get(target[0])
    if item is None or item.status != "ready":
        return []
    return [
        {
            **entry,
            "label": localize(entry["label"], locale),
            "detail": localize(entry["detail"], locale),
        }
        for entry in item.snapshot.get("sources", {}).get(target[1], [])
    ]


def fill_sources(manager, config) -> bool:
    changed = False
    for page in config.pages:
        target = reference(page.source)
        if target is None:
            continue
        entries, buttons = [], []
        for index, raw in enumerate(source_entries(manager, page.source)):
            action = Action(
                f"ext:{target[0]}/{raw['action']['id']}", raw["action"]["arguments"]
            )
            label = short(raw["label"], 24)
            entries.append(
                ListEntry(
                    raw["id"],
                    label,
                    short(raw["detail"], 40),
                    raw["icon"],
                    raw["color"],
                    raw["active"],
                    action,
                )
            )
            if index < 6:
                buttons.append(
                    ButtonConfig(
                        raw["id"],
                        index,
                        {"en": label, "fr": label},
                        raw["icon"],
                        raw["color"],
                        action=action,
                    )
                )
        if page.entries != entries or page.buttons != buttons:
            page.entries, page.buttons = entries, buttons
            changed = True
    return changed


def config_message(manager, config, locale: str) -> dict:
    payload = config.snapshot_payload(locale)
    for page, rendered in zip(config.pages, payload["pages"]):
        if reference(page.dashboard):
            rendered["dashboard"] = "extension"
        if reference(page.source):
            translated = {
                entry["id"]: entry
                for entry in source_entries(manager, page.source, locale)
            }
            for entry in (
                rendered["entries"] if page.layout == "list" else rendered["buttons"]
            ):
                raw = translated.get(entry["id"])
                if raw:
                    entry["label"] = short(raw["label"], 24)
                    if page.layout == "list":
                        entry["detail"] = short(raw["detail"], 40)
    # Multiple long lists share a 64 KiB console frame. Fairly trim the largest
    # generated lists first; the full source remains available to the editor.
    lists = [
        rendered["entries"]
        for page, rendered in zip(config.pages, payload["pages"])
        if reference(page.source) and page.layout == "list"
    ]
    size = len(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    while lists and size > 60000:
        longest = max(lists, key=len)
        if not longest:
            break
        removed = longest.pop()
        size -= len(
            json.dumps(removed, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        ) + bool(longest)
    return payload


def state_payload(manager, config) -> dict:
    panels, buttons = [], []
    for page in config.pages:
        target = reference(page.dashboard)
        if target:
            item = manager.items.get(target[0])
            panel = (
                item.snapshot.get("dashboards", {}).get(target[1])
                if item and item.status == "ready"
                else None
            )
            panels.append(
                {
                    "page": page.id,
                    **(
                        panel
                        or {
                            "title": {
                                "en": "Extension unavailable",
                                "fr": "Extension indisponible",
                            },
                            "status": "warning",
                            "cards": [
                                {
                                    "label": {
                                        "en": "Check Extensions on your PC",
                                        "fr": "Voir Extensions sur le PC",
                                    },
                                    "value": "--",
                                    "detail": {
                                        "en": "Enable or configure this integration",
                                        "fr": "Activez ou configurez cette intégration",
                                    },
                                }
                            ],
                        }
                    ),
                }
            )
        for button in page.buttons:
            target = reference(button.action.kind)
            if not target:
                continue
            item = manager.items.get(target[0])
            spec = (
                next(
                    (
                        spec
                        for spec in item.manifest["actions"]
                        if spec["id"] == target[1]
                    ),
                    None,
                )
                if item
                else None
            )
            ready = bool(item and item.status == "ready" and spec)
            active = (
                bool(item.snapshot.get("states", {}).get(spec.get("state")))
                if ready
                else False
            )
            if ready and reference(page.source):
                active = next(
                    (
                        entry["active"]
                        for entry in source_entries(manager, page.source)
                        if entry["id"] == button.id
                    ),
                    active,
                )
            buttons.append(
                {"page": page.id, "id": button.id, "available": ready, "active": active}
            )
    return {"extension_panels": panels, "extension_buttons": buttons}


def preview_payload(manager) -> dict:
    """Editor previews by contribution id, including unsaved page selections.

    Never expose generated action arguments: these may contain private tokens.
    """
    panels, sources = {}, {}
    for item in list(manager.items.values()):
        if item.status != "ready":
            continue
        prefix = f"ext:{item.manifest['id']}/"
        panels.update(
            {
                prefix + key: value
                for key, value in item.snapshot.get("dashboards", {}).items()
            }
        )
        for key, entries in item.snapshot.get("sources", {}).items():
            sources[prefix + key] = [
                {name: value for name, value in entry.items() if name != "action"}
                for entry in entries
            ]
    return {"extension_previews": panels, "extension_sources": sources}


def localized_state(payload: dict, locale: str) -> dict:
    if "extension_panels" not in payload:
        return payload
    panels = localize(payload["extension_panels"], locale)
    for panel in panels:
        panel["title"] = short(panel["title"], 64)
        for card in panel["cards"]:
            card["label"] = short(card["label"], 24)
            card["detail"] = short(card.get("detail", ""), 64)
    return {**payload, "extension_panels": panels}

"""Pages of the shared configuration contract."""

from __future__ import annotations

from typing import Any

from ..extensions.manifest import reference as extension_reference
from .actions import _parse_buttons
from .models import (
    DASHBOARDS,
    ICONS,
    MAX_ID,
    MAX_LABEL,
    MAX_PAGES,
    ConfigError,
    PageConfig,
)
from .primitives import _duplicates, _localised, _require_choice, _require_str


def _parse_page(raw: Any, index: int) -> PageConfig:
    context = f"pages[{index}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{context}: un objet est attendu")

    page_id = _require_str(raw.get("id"), f"{context}.id", MAX_ID)
    titles = _localised(raw.get("title", page_id), f"{context}.title", MAX_LABEL)

    dashboard = _require_choice(
        raw.get("dashboard", "auto"),
        f"{context}.dashboard",
        DASHBOARDS
        | (
            {raw.get("dashboard")}
            if extension_reference(raw.get("dashboard"))
            else set()
        ),
        f"Connus: {', '.join(sorted(DASHBOARDS))}",
        feminine=False,
    )
    page_icon = _require_choice(
        raw.get("icon", "page"),
        f"{context}.icon",
        ICONS,
        f"Connues: {', '.join(sorted(ICONS))}",
    )
    layout = _require_choice(
        raw.get("layout", "grid"),
        f"{context}.layout",
        ("grid", "list"),
        "Connues: grid, list",
    )
    source = _require_choice(
        raw.get("source", ""),
        f"{context}.source",
        (
            "",
            "windows",
            raw.get("source") if extension_reference(raw.get("source")) else "",
        ),
        "Connue: windows",
    )

    buttons = _parse_buttons(raw.get("buttons", []), context)

    return PageConfig(
        id=page_id,
        titles=titles,
        icon=page_icon,
        dashboard=dashboard,
        buttons=buttons,
        source=source,
        layout=layout,
    )


def _parse_pages(raw: Any) -> list[PageConfig]:
    if not isinstance(raw, list) or not raw:
        raise ConfigError("pages: une liste non vide est attendue")
    if len(raw) > MAX_PAGES:
        raise ConfigError(f"pages: {len(raw)} pages, maximum {MAX_PAGES}")

    pages = [_parse_page(item, index) for index, item in enumerate(raw)]

    duplicates = _duplicates([page.id for page in pages])
    if duplicates:
        raise ConfigError(f"pages: identifiants en double: {duplicates}")
    return pages


def _each_action(pages: list[PageConfig]):
    """Parcourt toutes les actions déclarées, appui long compris."""
    return (
        (page, button, action)
        for page in pages
        for button in page.buttons
        for action in (button.action, button.hold_action)
        if action is not None
    )


def _check_references(
    pages: list[PageConfig], kind: str, argument: str, known, complaint: str
) -> None:
    """Vérifie que les actions d'un type donné visent une cible existante.

    Une référence brisée ne se verrait qu'à l'appui du bouton, sur la console :
    la signaler au chargement évite ce détour. La navigation et les scripts
    partagent ce contrôle, seul le vocabulaire du message diffère.
    """
    for page, button, action in _each_action(pages):
        if action.kind != kind:
            continue
        target = action.args.get(argument)
        if target not in known:
            raise ConfigError(
                f"pages[{page.id}].{button.id}: {complaint.format(target=target)}"
            )

"""Actions of the shared configuration contract."""

from __future__ import annotations

import json
import math
from typing import Any

from ..extensions.manifest import reference as extension_reference
from ..keys import InvalidHotkey, parse_hotkey
from .arguments import WebUrlError, normalize_web_url
from .models import (
    DEFAULT_BUTTON_COLOR,
    ICONS,
    KNOWN_ACTIONS,
    MAX_BUTTONS_PER_PAGE,
    MAX_ID,
    MAX_LABEL,
    Action,
    ButtonConfig,
    ConfigError,
    action_arguments,
)
from .primitives import (
    _duplicates,
    _localised,
    _require_choice,
    _require_slot,
    _require_str,
)


def _split_action(raw: Any, context: str) -> tuple[str, dict[str, Any]]:
    """Sépare le type de l'action de ses arguments.

    Deux écritures sont acceptées : la forme abrégée `"media.play_pause"`,
    lorsque l'action n'a pas d'argument, et la forme complète `{"type": ...}`.
    """
    if isinstance(raw, str):
        return raw.strip(), {}
    if isinstance(raw, dict):
        kind = raw.get("type")
        if not isinstance(kind, str):
            raise ConfigError(f"{context}: champ 'type' manquant")
        return kind.strip(), {key: value for key, value in raw.items() if key != "type"}
    raise ConfigError(f"{context}: action invalide")


def _check_action_args(kind: str, args: dict[str, Any], context: str) -> None:
    """Valide les arguments d'une action et normalise ce qui peut l'être.

    Le contrôle a lieu au chargement plutôt qu'à l'usage : une erreur de frappe
    est ainsi signalée dans l'éditeur, et non à l'appui du bouton sur la console.
    `args` est modifié sur place lorsqu'une valeur admet une forme canonique.
    """
    arguments = action_arguments(kind)
    allowed = {argument["name"] for argument in arguments}
    unknown = set(args) - allowed
    if unknown:
        raise ConfigError(
            f"{context}: arguments inconnus pour '{kind}': {', '.join(sorted(unknown))}"
        )

    for argument in arguments:
        name = argument["name"]
        if argument.get("required") and name not in args:
            raise ConfigError(f"{context}: l'action '{kind}' exige '{name}'")

        if name not in args:
            continue

        value = args[name]
        field_type = argument.get("type")
        if field_type == "number":
            valid_number = type(value) in (int, float) and math.isfinite(value)
            if valid_number:
                minimum = argument.get("min", -math.inf)
                maximum = argument.get("max", math.inf)
                valid_number = minimum <= value <= maximum
            if not valid_number:
                raise ConfigError(
                    f"{context}.{name}: nombre attendu entre "
                    f"{argument.get('min', '-inf')} et {argument.get('max', '+inf')}"
                )
            continue

        if not isinstance(value, str):
            raise ConfigError(f"{context}.{name}: une chaine est attendue")
        if argument.get("required") and not value.strip():
            raise ConfigError(f"{context}.{name}: valeur obligatoire")
        maximum_length = argument.get("max_length", 2048)
        if maximum_length is not None and len(value) > maximum_length:
            raise ConfigError(
                f"{context}.{name}: longueur maximale {maximum_length} caracteres"
            )
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ConfigError(f"{context}.{name}: caractere de controle interdit")

        # Un raccourci mal écrit — `ctrl+alt+banane` — était accepté ici pour
        # n'échouer que sur la console. La forme retenue est normalisée, afin
        # que `shift+cmd+a` et `cmd+shift+a` ne donnent pas deux écritures.
        if field_type == "hotkey":
            try:
                args[name] = parse_hotkey(value).canonical()
            except InvalidHotkey as error:
                raise ConfigError(f"{context}.{name}: {error}") from error

        if kind == "url.open" and name == "url":
            try:
                args[name] = normalize_web_url(value)
            except WebUrlError as error:
                detail = (
                    "URL HTTP(S) uniquement"
                    if error.code == "http_only"
                    else "URL invalide"
                )
                raise ConfigError(f"{context}.{name}: {detail}") from error


def _parse_action(raw: Any, context: str) -> Action:
    if raw is None:
        return Action("noop")

    kind, args = _split_action(raw, context)
    if extension_reference(kind):
        try:
            encoded = json.dumps(args, allow_nan=False)
        except (ValueError, TypeError) as error:
            raise ConfigError(f"{context}: invalid extension arguments") from error
        if len(encoded) > 8192:
            raise ConfigError(f"{context}: extension arguments exceed 8 KiB")
        return Action(kind, args)
    if kind not in KNOWN_ACTIONS:
        known = ", ".join(sorted(KNOWN_ACTIONS))
        raise ConfigError(f"{context}: action inconnue '{kind}'. Connues: {known}")

    _check_action_args(kind, args, context)
    return Action(kind, args)


def _parse_button(raw: Any, index: int, context: str) -> ButtonConfig:
    if not isinstance(raw, dict):
        raise ConfigError(f"{context}: un objet est attendu")

    button_id = _require_str(raw.get("id"), f"{context}.id", MAX_ID)
    labels = _localised(raw.get("label", button_id), f"{context}.label", MAX_LABEL)

    slot = _require_slot(raw.get("slot", index), f"{context}.slot")
    icon = _require_choice(
        raw.get("icon", "app"),
        f"{context}.icon",
        ICONS,
        f"Connues: {', '.join(sorted(ICONS))}",
    )

    color = raw.get("color", DEFAULT_BUTTON_COLOR)
    if not isinstance(color, str) or not _is_hex_color(color):
        raise ConfigError(f"{context}.color: '{color}' n'est pas un code #RRGGBB")

    toggle = raw.get("toggle", "")
    if not isinstance(toggle, str):
        raise ConfigError(f"{context}.toggle: une chaine est attendue")

    raw_hold = raw.get("hold_label", "")
    hold_labels: dict[str, str] = {}
    if raw_hold:
        hold_labels = _localised(raw_hold, f"{context}.hold_label", MAX_LABEL)

    action = _parse_action(raw.get("action"), f"{context}.action")

    hold_action = None
    if raw.get("hold_action") is not None:
        hold_action = _parse_action(raw.get("hold_action"), f"{context}.hold_action")

    return ButtonConfig(
        id=button_id,
        slot=slot,
        labels=labels,
        icon=icon,
        color=color.upper(),
        toggle=toggle,
        hold_labels=hold_labels,
        action=action,
        hold_action=hold_action,
    )


def _is_hex_color(value: str) -> bool:
    if not value.startswith("#"):
        return False
    digits = value[1:]
    if len(digits) not in (3, 6):
        return False
    return all(character in "0123456789abcdefABCDEF" for character in digits)


def _parse_buttons(raw: Any, context: str) -> list[ButtonConfig]:
    """Boutons d'une page, emplacements et identifiants vérifiés uniques.

    Deux boutons partageant un emplacement en masqueraient un ; deux
    identifiants identiques rendraient l'un des deux inatteignable.
    """
    if not isinstance(raw, list):
        raise ConfigError(f"{context}.buttons: une liste est attendue")
    if len(raw) > MAX_BUTTONS_PER_PAGE:
        raise ConfigError(
            f"{context}.buttons: {len(raw)} boutons, maximum {MAX_BUTTONS_PER_PAGE}"
        )

    buttons = [
        _parse_button(item, position, f"{context}.buttons[{position}]")
        for position, item in enumerate(raw)
    ]

    duplicates = _duplicates([button.slot for button in buttons])
    if duplicates:
        raise ConfigError(f"{context}: emplacements en double: {duplicates}")

    duplicate_ids = _duplicates([button.id for button in buttons])
    if duplicate_ids:
        raise ConfigError(f"{context}: identifiants en double: {duplicate_ids}")

    return buttons

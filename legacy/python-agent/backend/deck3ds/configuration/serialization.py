"""Serialization of the shared configuration contract."""

from __future__ import annotations

from typing import Any

from .models import FEATURE_SPECS, LOCALES, Action, ButtonConfig, Config, PageConfig


def _localised_to_raw(texts: dict[str, str]) -> Any:
    """Réécrit un texte localisé sous sa forme la plus concise.

    Une valeur identique dans toutes les langues redevient une simple chaîne :
    le fichier reste lisible et ne s'alourdit pas de traductions inutiles.
    """
    if not texts:
        return ""

    values = {texts.get(locale, "") for locale in LOCALES}
    if len(values) == 1:
        return texts.get("en", "")

    return {locale: texts.get(locale, "") for locale in LOCALES}


def _action_to_raw(action: Action | None) -> Any:
    """Réécrit une action sous sa forme la plus concise."""
    if action is None:
        return None
    if not action.args:
        return action.kind
    return {"type": action.kind, **action.args}


def _button_to_raw(button: ButtonConfig) -> dict[str, Any]:
    """Écriture concise d'un bouton : les valeurs par défaut sont omises."""
    raw: dict[str, Any] = {
        "id": button.id,
        "slot": button.slot,
        "label": _localised_to_raw(button.labels),
        "icon": button.icon,
        "color": button.color,
    }
    if button.toggle:
        raw["toggle"] = button.toggle
    if button.hold_labels:
        raw["hold_label"] = _localised_to_raw(button.hold_labels)

    raw["action"] = _action_to_raw(button.action)
    if button.hold_action is not None:
        raw["hold_action"] = _action_to_raw(button.hold_action)
    return raw


def _page_to_raw(page: PageConfig) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "id": page.id,
        "title": _localised_to_raw(page.titles),
        "icon": page.icon,
        "dashboard": page.dashboard,
    }
    if page.layout != "grid":
        raw["layout"] = page.layout
    if page.source:
        raw["source"] = page.source

    # Le contenu d'une page dynamique appartient à l'état d'exécution, pas au
    # fichier. Sans cette frontière, ouvrir l'éditeur puis enregistrer un autre
    # réglage inscrirait les fenêtres du moment dans `config.json`.
    if page.source:
        raw["buttons"] = []
    else:
        # Les boutons sont rangés par emplacement : le fichier reflète alors
        # l'ordre visible sur la console.
        raw["buttons"] = [
            _button_to_raw(button)
            for button in sorted(page.buttons, key=lambda item: item.slot)
        ]
    return raw


def to_raw(config: Config) -> dict[str, Any]:
    """Reconstruit la structure du fichier depuis une configuration chargée.

    Cette fonction est l'inverse de `parse` : elle permet à l'interface de
    relire, modifier puis réenregistrer la configuration sans en perdre le
    contenu ni la mise en forme concise.
    """
    raw: dict[str, Any] = {
        "revision": config.revision,
        "server": {
            "host": config.host,
            "port": config.port,
            "token": config.token,
            "poll_interval": config.poll_interval,
            "volume_step": config.volume_step,
        },
        "features": {name: getattr(config.features, name) for name in FEATURE_SPECS},
        "integrations": {
            "obs": {
                "enabled": config.obs.enabled,
                "host": config.obs.host,
                "port": config.obs.port,
                "password": config.obs.password,
                "timeout": config.obs.timeout,
            }
        },
    }

    if config.scripts:
        raw["scripts"] = {
            name: list(command) for name, command in config.scripts.items()
        }

    raw["pages"] = [_page_to_raw(page) for page in config.pages]
    return raw

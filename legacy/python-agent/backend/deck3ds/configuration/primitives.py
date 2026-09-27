"""Primitives of the shared configuration contract."""

from __future__ import annotations

from typing import Any

from .models import (
    LOCALES,
    MAX_BUTTONS_PER_PAGE,
    PORT_RANGE,
    VOLUME_STEP_RANGE,
    ConfigError,
)


def _localised(value: Any, context: str, max_length: int) -> dict[str, str]:
    """Lit un texte pouvant être décliné par langue.

    Deux écritures sont acceptées :

    - une chaîne simple, utilisée quelle que soit la langue ;
    - un objet associant un code de langue à son texte, par exemple
      ``{"en": "Browser", "fr": "Navigateur"}``.

    La seconde forme permet de traduire les libellés définis par l'utilisateur,
    que le catalogue interne de l'application ne peut pas connaître.
    """
    if isinstance(value, str):
        text = _require_str(value, context, max_length)
        return {locale: text for locale in LOCALES}

    if not isinstance(value, dict):
        raise ConfigError(f"{context}: une chaine ou un objet par langue est attendu")

    unknown = set(value) - set(LOCALES)
    if unknown:
        raise ConfigError(
            f"{context}: langues inconnues {sorted(unknown)}. "
            f"Connues: {', '.join(LOCALES)}"
        )

    if "en" not in value:
        # L'anglais sert de repli universel : l'exiger évite un libellé vide
        # pour une langue non renseignée.
        raise ConfigError(f"{context}: la variante 'en' est obligatoire")

    texts: dict[str, str] = {}
    for locale in LOCALES:
        raw_text = value.get(locale, value["en"])
        texts[locale] = _require_str(raw_text, f"{context}.{locale}", max_length)
    return texts


def _require_str(value: Any, context: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{context}: une chaine est attendue")
    text = value.strip()
    if not text:
        raise ConfigError(f"{context}: valeur vide")
    if len(text) > max_length:
        raise ConfigError(f"{context}: {len(text)} caracteres, maximum {max_length}")
    return text


def _require_int(value: Any, context: str) -> int:
    """Entier strict.

    `isinstance(True, int)` vaut vrai en Python : sans la garde explicite, un
    booléen passerait pour un entier et `true` serait accepté comme numéro de
    port.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{context}: un entier est attendu")
    return value


def _require_port(value: Any, context: str) -> int:
    port = _require_int(value, context)
    low, high = PORT_RANGE
    if not low <= port <= high:
        raise ConfigError(f"{context}: {port} hors bornes")
    return port


def _require_host(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context}: adresse invalide")
    return value.strip()


def _require_choice(
    value: Any, context: str, allowed, listing: str, feminine: bool = True
) -> str:
    """Valeur appartenant à un ensemble connu.

    `listing` est l'énumération présentée à l'utilisateur : la lui donner évite
    de deviner ce qui était attendu. L'accord suit le genre du terme désigné —
    « icône inconnue », « dashboard inconnu ».
    """
    if not isinstance(value, str) or value not in allowed:
        adjective = "inconnue" if feminine else "inconnu"
        raise ConfigError(f"{context}: '{value}' {adjective}. {listing}")
    return value


def _require_slot(value: Any, context: str) -> int:
    """Emplacement d'un bouton sur la grille de la console."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{context}: un entier est attendu")
    if not 0 <= value < MAX_BUTTONS_PER_PAGE:
        raise ConfigError(
            f"{context}: {value} hors bornes (0 a {MAX_BUTTONS_PER_PAGE - 1})"
        )
    return value


def _require_step(value: Any, context: str) -> int:
    """Pas de réglage du volume, borné."""
    low, high = VOLUME_STEP_RANGE
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{context}: entier entre {low} et {high}")
    if not low <= value <= high:
        raise ConfigError(f"{context}: entier entre {low} et {high}")
    return value


def _require_seconds(value: Any, context: str, low: float, high: float) -> float:
    """Durée en secondes, bornée."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{context}: un nombre est attendu")
    seconds = float(value)
    if not low <= seconds <= high:
        raise ConfigError(f"{context}: entre {low} et {high:g} secondes")
    return seconds


def _duplicates(values: list[Any]) -> list[Any]:
    """Valeurs apparaissant plus d'une fois, triées pour un message stable."""
    return sorted({value for value in values if values.count(value) > 1})

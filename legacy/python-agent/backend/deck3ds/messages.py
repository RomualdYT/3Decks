"""Messages renvoyés à la console.

Ces textes s'affichent en notification sur l'écran de la 3DS : ils doivent donc
suivre la langue choisie par l'utilisateur. La console annonce sa langue lors du
handshake, et l'agent s'y conforme.

L'anglais est la langue par défaut, cohérente avec le reste du projet.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_CATALOGUE: dict[str, dict[str, str]] = {
    "en": {
        "volume_set": "Volume {value}%",
        "volume_adjusted": "Volume adjusted",
        "music_set": "Music {value}%",
        "sound_muted": "Sound muted",
        "sound_restored": "Sound on",
        "mic_muted": "Mic muted",
        "mic_active": "Mic live",
        "play_pause": "Play / Pause",
        "next_track": "Next track",
        "previous_track": "Previous track",
        "app_closed": "{target} closed",
        "link_opened": "Link opened",
        "opened": "Opened",
        "locked": "Session locked",
        "missing_target": "missing target",
        "missing_url": "missing URL",
        "missing_path": "missing path",
        "missing_keys": "missing shortcut",
        "missing_page": "missing page",
        "missing_output": "missing output",
        "missing_window": "missing window",
        "unknown_script": "unknown script: {name}",
        "unhandled": "unsupported action: {kind}",
        "error": "error: {kind}",
        "single_output": "only one output available",
        "output_not_found": "output not found: {name}",
        "window_not_found": "window not found: {name}",
        "app_volume_unreadable": "player volume cannot be read",
        "invalid_app": "invalid application name",
        "invalid_url": "invalid URL",
        "http_only": "only HTTP and HTTPS URLs are allowed",
        "invalid_target": "invalid target",
        "target_open_failed": "could not open target",
        "obs_disabled": "OBS integration is not configured",
        "obs_missing_scene": "missing OBS scene",
        "obs_missing_source": "missing OBS source",
        "obs_scene_set": "OBS scene: {scene}",
        "obs_stream_toggled": "OBS stream toggled",
        "obs_record_toggled": "OBS recording toggled",
        "obs_source_toggled": "OBS source toggled: {source}",
    },
    "fr": {
        "volume_set": "Volume {value} %",
        "volume_adjusted": "Volume ajusté",
        "music_set": "Musique {value} %",
        "sound_muted": "Son coupé",
        "sound_restored": "Son rétabli",
        "mic_muted": "Micro coupé",
        "mic_active": "Micro actif",
        "play_pause": "Lecture / Pause",
        "next_track": "Piste suivante",
        "previous_track": "Piste précédente",
        "app_closed": "{target} fermé",
        "link_opened": "Lien ouvert",
        "opened": "Ouvert",
        "locked": "Session verrouillée",
        "missing_target": "cible manquante",
        "missing_url": "URL manquante",
        "missing_path": "chemin manquant",
        "missing_keys": "combinaison manquante",
        "missing_page": "page manquante",
        "missing_output": "sortie manquante",
        "missing_window": "fenêtre manquante",
        "unknown_script": "script inconnu : {name}",
        "unhandled": "action non gérée : {kind}",
        "error": "erreur : {kind}",
        "single_output": "une seule sortie disponible",
        "output_not_found": "sortie introuvable : {name}",
        "window_not_found": "fenêtre introuvable : {name}",
        "app_volume_unreadable": "volume du lecteur illisible",
        "invalid_app": "nom d'application invalide",
        "invalid_url": "URL invalide",
        "http_only": "seules les URL HTTP et HTTPS sont autorisées",
        "invalid_target": "cible invalide",
        "target_open_failed": "impossible d'ouvrir la cible",
        "obs_disabled": "intégration OBS non configurée",
        "obs_missing_scene": "scène OBS manquante",
        "obs_missing_source": "source OBS manquante",
        "obs_scene_set": "Scène OBS : {scene}",
        "obs_stream_toggled": "Diffusion OBS basculée",
        "obs_record_toggled": "Enregistrement OBS basculé",
        "obs_source_toggled": "Source OBS basculée : {source}",
    },
}

def _normalise_language(code: str) -> str:
    normalised = (code or "").strip().lower()[:2]
    return normalised if normalised in _CATALOGUE else "en"


# La langue est locale au contexte d'exécution. Les actions de consoles
# différentes peuvent s'exécuter simultanément dans des threads distincts sans
# modifier les messages l'une de l'autre.
_language: ContextVar[str] = ContextVar("deck3ds_message_language", default="en")


def set_language(code: str) -> None:
    """Choisit la langue du contexte courant (compatibilité et tests)."""
    _language.set(_normalise_language(code))


@contextmanager
def using_language(code: str) -> Iterator[None]:
    """Isole temporairement la langue d'une exécution d'action."""
    token = _language.set(_normalise_language(code))
    try:
        yield
    finally:
        _language.reset(token)


def language() -> str:
    return _language.get()


def msg(key: str, **values: object) -> str:
    """Message traduit, avec substitution des valeurs.

    Une clé absente retombe sur l'anglais, puis sur la clé elle-même : mieux
    vaut un texte imparfait qu'une notification vide.
    """
    table = _CATALOGUE.get(_language.get(), _CATALOGUE["en"])
    template = table.get(key) or _CATALOGUE["en"].get(key) or key

    if not values:
        return template

    try:
        return template.format(**values)
    except (KeyError, IndexError):
        return template

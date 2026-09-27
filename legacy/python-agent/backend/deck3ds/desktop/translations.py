"""Concise native-menu copy in the two languages supported by 3Decks."""

from __future__ import annotations

import locale
import os
import subprocess
import sys


COPY = {
    "fr": {
        "starting": "Démarrage de l’agent…",
        "stopping": "Arrêt de l’agent…",
        "paused": "Commandes suspendues",
        "degraded": "Agent actif · attention requise",
        "ready_none": "Agent actif · aucune console",
        "ready_one": "Agent actif · 1 console connectée",
        "ready_many": "Agent actif · {count} consoles connectées",
        "open": "Ouvrir 3Decks",
        "connect": "Connecter une console…",
        "resume": "Reprendre les commandes",
        "pause": "Suspendre les commandes",
        "pause_15": "Pendant 15 minutes",
        "pause_60": "Pendant 1 heure",
        "pause_until": "Jusqu’à réactivation",
        "quick": "Réglages rapides",
        "notifications": "Notifications",
        "media": "Musique et médias",
        "windows": "Fenêtres ouvertes",
        "system_stats": "Performances du PC",
        "obs": "OBS Studio",
        "autostart": "Lancer à l’ouverture de session",
        "diagnostics": "Diagnostic",
        "open_status": "Ouvrir l’état de l’agent",
        "copy_address": "Copier l’adresse de connexion",
        "open_logs": "Ouvrir le journal",
        "restart": "Redémarrer l’agent",
        "updates": "Rechercher une mise à jour…",
        "quit": "Quitter 3Decks",
        "copied": "Adresse copiée",
        "error": "L’action n’a pas pu être effectuée.",
        "tooltip_none": "3Decks — aucune console",
        "tooltip_one": "3Decks — 1 console connectée",
        "tooltip_many": "3Decks — {count} consoles connectées",
        "tooltip_paused": "3Decks — commandes suspendues",
    },
    "en": {
        "starting": "Starting agent…",
        "stopping": "Stopping agent…",
        "paused": "Controls suspended",
        "degraded": "Agent running · attention required",
        "ready_none": "Agent running · no console",
        "ready_one": "Agent running · 1 console connected",
        "ready_many": "Agent running · {count} consoles connected",
        "open": "Open 3Decks",
        "connect": "Connect a console…",
        "resume": "Resume controls",
        "pause": "Suspend controls",
        "pause_15": "For 15 minutes",
        "pause_60": "For 1 hour",
        "pause_until": "Until resumed",
        "quick": "Quick settings",
        "notifications": "Notifications",
        "media": "Music and media",
        "windows": "Open windows",
        "system_stats": "Computer performance",
        "obs": "OBS Studio",
        "autostart": "Launch at login",
        "diagnostics": "Diagnostics",
        "open_status": "Open agent status",
        "copy_address": "Copy connection address",
        "open_logs": "Open log",
        "restart": "Restart agent",
        "updates": "Check for updates…",
        "quit": "Quit 3Decks",
        "copied": "Address copied",
        "error": "The action could not be completed.",
        "tooltip_none": "3Decks — no console",
        "tooltip_one": "3Decks — 1 console connected",
        "tooltip_many": "3Decks — {count} consoles connected",
        "tooltip_paused": "3Decks — controls suspended",
    },
}


def preferred_language() -> str:
    """Resolve the OS language without importing a native GUI framework."""

    override = os.environ.get("DECK3DS_LOCALE", "").lower()
    if override.startswith(("fr", "en")):
        return override[:2]

    language = locale.getlocale()[0] or ""
    if not language and sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["/usr/bin/defaults", "read", "-g", "AppleLocale"],
                capture_output=True,
                text=True,
                timeout=1,
                check=False,
            )
            language = result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    return "fr" if language.lower().startswith("fr") else "en"


def translate(language: str, key: str, **values: object) -> str:
    text = COPY["fr" if language == "fr" else "en"][key]
    return text.format(**values)

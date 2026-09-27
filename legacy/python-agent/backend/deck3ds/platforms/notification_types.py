"""Types et règles partagés par les fournisseurs de notifications."""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

from dataclasses import dataclass

#: Notifications conservées et transmises à la console.
MAX_NOTIFICATIONS = 8

#: Au-delà, une notification n'a plus d'intérêt immédiat.
MAX_AGE_SECONDS = 6 * 3600

_APP_ICONS = {
    "Messages": "chat",
    "Mail": "page",
    "FaceTime": "video",
    "Rappels": "star",
    "Calendrier": "page",
    "Musique": "music",
    "Apple Music": "music",
    "Spotify": "music",
    "Podcasts": "music",
    "Slack": "chat",
    "Discord": "chat",
    "Safari": "browser",
    "Chrome": "browser",
    "Edge": "browser",
    "Firefox": "browser",
    "ChatGPT": "app",
    "Codex": "terminal",
    "VS Code": "app",
    "Docker": "app",
    "Finder": "folder",
    "Explorateur": "folder",
    "Terminal": "terminal",
    "GitHub": "app",
}


@dataclass(frozen=True)
class Notification:
    """Notification normalisée, indépendante de sa source système."""

    app: str
    title: str
    body: str
    icon: str
    age: int
    bundle: str
    key: str


def icon_for_app(name: str) -> str:
    """Icône 3DS correspondant au nom lisible d'une application."""
    return _APP_ICONS.get(name, "star")

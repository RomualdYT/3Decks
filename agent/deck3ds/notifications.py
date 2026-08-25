"""Lecture des notifications de macOS.

macOS conserve les notifications du centre de notifications dans une base
SQLite, dont le contenu est un plist binaire. Les deux formats sont pris en
charge par la bibliothèque standard : aucune dépendance n'est nécessaire.

Réserve importante : cette base est un détail d'implémentation du système, non
documenté par Apple. Son schéma peut changer lors d'une mise à jour majeure de
macOS. Le décodage est donc volontairement défensif : en cas de structure
inattendue, la fonctionnalité se désactive au lieu de faire échouer l'agent.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import os
import plistlib
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

#: Emplacement de la base du centre de notifications.
_DB_PATH = (
    "~/Library/Group Containers/group.com.apple.usernoted/db2/db"
)

#: Les dates sont comptées depuis le 1er janvier 2001, référence d'Apple.
_APPLE_EPOCH = 978307200

#: Notifications conservées et transmises à la console.
MAX_NOTIFICATIONS = 8

#: Au-delà, une notification n'a plus d'intérêt immédiat.
MAX_AGE_SECONDS = 6 * 3600

#: Noms lisibles pour les applications courantes. L'identifiant de paquet est
#: illisible sur un petit écran.
_APP_NAMES = {
    "com.apple.mobilesms": "Messages",
    "com.apple.mail": "Mail",
    "com.apple.facetime": "FaceTime",
    "com.apple.reminders": "Rappels",
    "com.apple.iCal": "Calendrier",
    "com.apple.music": "Musique",
    "com.apple.podcasts": "Podcasts",
    "com.apple.news": "News",
    "com.apple.finder": "Finder",
    "com.apple.Safari": "Safari",
    "com.apple.systempreferences": "Réglages",
    "com.tinyspeck.slackmacgap": "Slack",
    "com.hnc.Discord": "Discord",
    "com.spotify.client": "Spotify",
    "com.openai.chat": "ChatGPT",
    "com.openai.codex": "Codex",
    "com.microsoft.VSCode": "VS Code",
    "com.google.Chrome": "Chrome",
    "com.docker.docker": "Docker",
    "com.github.GitHubClient": "GitHub",
}

#: Icônes de l'interface associées aux applications connues.
_APP_ICONS = {
    "Messages": "chat",
    "Mail": "page",
    "FaceTime": "video",
    "Rappels": "star",
    "Calendrier": "page",
    "Musique": "music",
    "Spotify": "music",
    "Podcasts": "music",
    "Slack": "chat",
    "Discord": "chat",
    "Safari": "browser",
    "Chrome": "browser",
    "ChatGPT": "app",
    "Codex": "terminal",
    "VS Code": "app",
    "Docker": "app",
    "Finder": "folder",
    "GitHub": "app",
}


@dataclass
class Notification:
    """Notification prête à être affichée."""

    app: str
    title: str
    body: str
    icon: str
    #: Ancienneté en secondes, arrondie.
    age: int
    #: Identifiant de paquet, pour ouvrir l'application concernée.
    bundle: str
    #: Empreinte servant à détecter les doublons et les nouveautés.
    key: str

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "app": self.app,
            "title": self.title,
            "icon": self.icon,
            "age": self.age,
        }
        if self.body:
            payload["body"] = self.body
        return payload


def _readable_name(bundle: str) -> str:
    """Nom lisible d'une application à partir de son identifiant de paquet."""
    # Les notifications du système portent un préfixe technique.
    cleaned = bundle.split(":")[-1] if ":" in bundle else bundle

    known = _APP_NAMES.get(cleaned)
    if known:
        return known

    # À défaut, le dernier segment de l'identifiant est le plus parlant.
    tail = cleaned.rsplit(".", 1)[-1]
    return tail[:1].upper() + tail[1:] if tail else cleaned


def _icon_for(name: str) -> str:
    return _APP_ICONS.get(name, "star")


class NotificationReader:
    """Lecture périodique des notifications, avec déduplication.

    Les notifications identiques répétées sont fusionnées : certaines
    applications en émettent plusieurs d'affilée, ce qui saturerait l'écran de
    la console.

    `ignored` permet d'écarter des applications par nom ou par identifiant de
    paquet. Aucune clé de configuration ne l'alimente aujourd'hui ; le
    paramètre existe pour que l'appelant puisse le faire.
    """

    def __init__(self, ignored: list[str] | None = None) -> None:
        self.path = Path(os.path.expanduser(_DB_PATH))
        self.available = self.path.is_file()
        #: Vrai après un échec de lecture : on cesse alors d'insister.
        self.broken = False

        # Comparaison en minuscules, pour rester tolérant à la casse.
        self._ignored = {name.strip().lower() for name in (ignored or [])}

        #: Empreinte de la notification la plus récente déjà vue.
        self._last_key = ""

    def _is_ignored(self, app: str, bundle: str) -> bool:
        if not self._ignored:
            return False
        return (
            app.lower() in self._ignored or bundle.lower() in self._ignored
        )

    def read(self) -> list[Notification]:
        """Notifications récentes, de la plus récente à la plus ancienne."""
        if not self.available or self.broken:
            return []

        try:
            # Ouverture en lecture seule : la base appartient au système et ne
            # doit sous aucun prétexte être modifiée.
            connection = sqlite3.connect(
                f"file:{self.path}?mode=ro", uri=True, timeout=1.0
            )
        except sqlite3.Error:
            self.broken = True
            return []

        try:
            rows = connection.execute(
                "SELECT rec.delivered_date, app.identifier, rec.data "
                "FROM record rec JOIN app ON rec.app_id = app.app_id "
                "WHERE rec.delivered_date IS NOT NULL "
                "ORDER BY rec.delivered_date DESC LIMIT 40"
            ).fetchall()
        except sqlite3.Error:
            # Schéma inattendu : la fonctionnalité s'éteint proprement plutôt
            # que de réessayer indéfiniment.
            self.broken = True
            return []
        finally:
            connection.close()

        now = time.time()
        results: list[Notification] = []
        seen: set[str] = set()

        for delivered, bundle, blob in rows:
            notification = self._decode(delivered, bundle or "", blob, now)
            if notification is None:
                continue

            # Déduplication : une même notification répétée n'apparaît qu'une
            # fois, seule la plus récente étant conservée.
            if notification.key in seen:
                continue
            seen.add(notification.key)

            results.append(notification)
            if len(results) >= MAX_NOTIFICATIONS:
                break

        return results

    def _decode(
        self, delivered: float, bundle: str, blob: bytes, now: float
    ) -> Notification | None:
        """Convertit une ligne de la base en notification affichable."""
        if not isinstance(delivered, (int, float)) or not blob:
            return None

        age = now - (float(delivered) + _APPLE_EPOCH)
        if age < 0.0:
            age = 0.0
        if age > MAX_AGE_SECONDS:
            return None

        try:
            decoded = plistlib.loads(blob)
        except Exception:
            # Contenu illisible : on ignore cette entrée sans rien interrompre.
            return None

        if not isinstance(decoded, dict):
            return None

        request = decoded.get("req")
        if not isinstance(request, dict):
            return None

        def text(field: str) -> str:
            value = request.get(field)
            return value.strip() if isinstance(value, str) else ""

        title = text("titl")
        subtitle = text("subt")
        body = text("body")

        # Une notification sans titre ni corps n'apporte rien.
        if not title and not body:
            return None

        app = _readable_name(bundle)
        if self._is_ignored(app, bundle):
            return None

        # Le sous-titre précise souvent le titre : on les réunit plutôt que de
        # perdre l'information.
        if subtitle and subtitle != title:
            body = f"{subtitle} — {body}" if body else subtitle

        return Notification(
            app=app,
            title=title or app,
            body=body,
            icon=_icon_for(app),
            age=int(age),
            bundle=bundle,
            key=f"{bundle}|{title}|{body}",
        )

    def take_new(self, notifications: list[Notification]) -> Notification | None:
        """Retourne la notification à annoncer, si elle vient d'arriver.

        La comparaison porte sur l'empreinte de la plus récente : au premier
        appel, aucune annonce n'est faite, afin de ne pas signaler l'historique
        au démarrage de l'agent.
        """
        if not notifications:
            return None

        newest = notifications[0]

        if not self._last_key:
            self._last_key = newest.key
            return None

        if newest.key == self._last_key:
            return None

        self._last_key = newest.key
        return newest

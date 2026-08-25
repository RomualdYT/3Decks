"""Lecture des notifications du système.

macOS et Windows conservent tous deux leurs notifications dans une base SQLite,
lisible sans dépendance : seuls le chemin, la requête, l'origine des dates et le
format de la charge utile diffèrent. Un lecteur commun porte la logique partagée
— déduplication, filtrage par ancienneté, détection des nouveautés — et délègue
ces quatre différences à un adaptateur par système.

- macOS : `~/Library/Group Containers/group.com.apple.usernoted/db2/db`,
  charge utile en plist binaire, dates comptées depuis 2001.
- Windows : `%LOCALAPPDATA%/Microsoft/Windows/Notifications/wpndatabase.db`,
  charge utile en XML de toast, dates en FILETIME comptées depuis 1601.

Réserve importante : ces bases sont des détails d'implémentation, non documentés
par leurs éditeurs. Leur schéma peut changer lors d'une mise à jour majeure. Le
décodage est donc volontairement défensif : devant une structure inattendue, la
fonctionnalité se désactive au lieu de faire échouer l'agent.

Sur Windows, l'API `UserNotificationListener` aurait été plus propre, mais elle
exige une identité de paquet et un appel depuis un fil d'interface : un agent
lancé depuis un dossier ne peut pas y prétendre.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import os
import plistlib
import sqlite3
import sys
import time
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path

#: Base du centre de notifications de macOS.
_MAC_DB_PATH = "~/Library/Group Containers/group.com.apple.usernoted/db2/db"

#: Base des notifications poussées de Windows, depuis la version 1607. Les
#: éditions antérieures utilisaient `appdb.dat`, dans un format propriétaire :
#: elles ne sont pas prises en charge.
_WINDOWS_DB_PATH = (
    "~/AppData/Local/Microsoft/Windows/Notifications/wpndatabase.db"
)

#: Les dates de macOS sont comptées depuis le 1er janvier 2001.
_APPLE_EPOCH = 978307200

#: Un FILETIME Windows compte les intervalles de 100 ns depuis le
#: 1er janvier 1601. Cette constante est l'écart avec l'époque Unix.
_FILETIME_EPOCH = 11644473600
_FILETIME_PER_SECOND = 10_000_000

#: Notifications conservées et transmises à la console.
MAX_NOTIFICATIONS = 8

#: Au-delà, une notification n'a plus d'intérêt immédiat.
MAX_AGE_SECONDS = 6 * 3600

#: Avance tolérée sur l'horloge, la date de la base et l'heure courante n'étant
#: pas lues au même instant. Au-delà, la date est jugée aberrante.
_CLOCK_TOLERANCE = 60.0

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

#: Noms lisibles des applications Windows. L'identifiant y est un AUMID, dont la
#: forme varie : identifiant de paquet du Microsoft Store, ou chemin du
#: raccourci pour une application installée classiquement.
_WINDOWS_APP_NAMES = {
    "microsoft.windowscommunicationsapps": "Courrier",
    "microsoft.windowsstore": "Store",
    "microsoft.skypeapp": "Skype",
    "microsoft.outlook": "Outlook",
    "microsoft.teams": "Teams",
    "microsoft.office.outlook": "Outlook",
    "microsoft.windows.explorer": "Explorateur",
    "microsoft.windowsterminal": "Terminal",
    "windows.systemtoast.securityandmaintenance": "Sécurité",
    "windows.systemtoast.windowsupdate": "Mise à jour",
    "windows.systemtoast.bthquickpair": "Bluetooth",
    "chrome": "Chrome",
    "firefox": "Firefox",
    "msedge": "Edge",
    "discord": "Discord",
    "slack": "Slack",
    "spotify": "Spotify",
    "code": "VS Code",
    "steam": "Steam",
    "thunderbird": "Thunderbird",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
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


def _readable_windows_name(aumid: str) -> str:
    """Nom lisible d'une application Windows à partir de son AUMID.

    Trois formes se présentent : un identifiant de paquet du Store
    (`Microsoft.WindowsStore_8wekyb3d8bbwe!App`), un identifiant de notification
    système (`Windows.SystemToast.WindowsUpdate`), ou le chemin d'un raccourci
    (`{...}\Programs\Discord.lnk`). Chacune est réduite au fragment porteur de
    sens avant d'être confrontée à la table.
    """
    cleaned = aumid.strip()
    if not cleaned:
        return ""

    # Un AUMID du Store sépare le paquet du point d'entrée par « ! ».
    package = cleaned.split("!")[0]
    # Le suffixe d'éditeur (`_8wekyb3d8bbwe`) n'apporte rien.
    package = package.split("_")[0]

    # Forme « chemin de raccourci » : seul le nom du fichier compte.
    if "\\" in package or "/" in package:
        package = package.replace("\\", "/").rsplit("/", 1)[-1]
    if package.lower().endswith(".lnk"):
        package = package[: -len(".lnk")]
    if package.lower().endswith(".exe"):
        package = package[: -len(".exe")]

    known = _WINDOWS_APP_NAMES.get(package.lower())
    if known:
        return known

    # Les notifications système annoncent leur origine dans le dernier segment.
    tail = package.rsplit(".", 1)[-1] if "." in package else package
    return tail[:1].upper() + tail[1:] if tail else package


def _icon_for(name: str) -> str:
    return _APP_ICONS.get(name, "star")


class _Source:
    """Différences d'un système : où lire, quoi lire, comment décoder.

    Un adaptateur ne connaît rien de la déduplication ni du filtrage : il
    traduit une ligne de la base en notification, ou rend `None` si la ligne
    n'est pas exploitable.
    """

    #: Emplacement de la base, avant expansion du dossier personnel.
    path = ""

    #: Requête retournant `(date, application, charge utile)`, la plus récente
    #: d'abord. La limite est large : beaucoup de lignes sont écartées ensuite.
    query = ""

    def timestamp(self, raw: object) -> float | None:
        """Convertit la date de la base en secondes depuis l'époque Unix."""
        raise NotImplementedError

    def texts(self, payload: object) -> tuple[str, str, str]:
        """Extrait `(titre, sous-titre, corps)` de la charge utile."""
        raise NotImplementedError

    def app_name(self, identifier: str) -> str:
        """Nom lisible de l'application émettrice."""
        raise NotImplementedError


class _MacSource(_Source):
    """Centre de notifications de macOS : plist binaire, époque 2001."""

    path = _MAC_DB_PATH
    query = (
        "SELECT rec.delivered_date, app.identifier, rec.data "
        "FROM record rec JOIN app ON rec.app_id = app.app_id "
        "WHERE rec.delivered_date IS NOT NULL "
        "ORDER BY rec.delivered_date DESC LIMIT 40"
    )

    def timestamp(self, raw: object) -> float | None:
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            return None
        return float(raw) + _APPLE_EPOCH

    def texts(self, payload: object) -> tuple[str, str, str]:
        if not isinstance(payload, (bytes, bytearray)):
            return "", "", ""
        try:
            decoded = plistlib.loads(bytes(payload))
        except Exception:
            # Contenu illisible : cette entrée est ignorée, sans rien rompre.
            return "", "", ""

        if not isinstance(decoded, dict):
            return "", "", ""
        request = decoded.get("req")
        if not isinstance(request, dict):
            return "", "", ""

        def text(field: str) -> str:
            value = request.get(field)
            return value.strip() if isinstance(value, str) else ""

        return text("titl"), text("subt"), text("body")

    def app_name(self, identifier: str) -> str:
        return _readable_name(identifier)


class _WindowsSource(_Source):
    """Notifications poussées de Windows : XML de toast, dates en FILETIME."""

    path = _WINDOWS_DB_PATH
    # `NotificationHandler` porte le nom de l'application, `Notification` la
    # charge utile : la jointure relie les deux.
    query = (
        "SELECT n.ArrivalTime, h.PrimaryId, n.Payload "
        "FROM Notification n "
        "JOIN NotificationHandler h ON n.HandlerId = h.RecordId "
        "WHERE n.ArrivalTime IS NOT NULL AND n.ArrivalTime > 0 "
        "ORDER BY n.ArrivalTime DESC LIMIT 40"
    )

    def timestamp(self, raw: object) -> float | None:
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            return None
        return float(raw) / _FILETIME_PER_SECOND - _FILETIME_EPOCH

    def texts(self, payload: object) -> tuple[str, str, str]:
        if isinstance(payload, (bytes, bytearray)):
            try:
                raw = bytes(payload).decode("utf-8")
            except UnicodeDecodeError:
                return "", "", ""
        elif isinstance(payload, str):
            raw = payload
        else:
            return "", "", ""

        try:
            root = ElementTree.fromstring(raw)
        except ElementTree.ParseError:
            return "", "", ""

        # Seules les notifications d'écran nous intéressent : une vignette de
        # menu Démarrer (`tile`) ou un badge ne s'affiche pas comme une alerte.
        if root.tag != "toast":
            return "", "", ""

        # Un toast expose ses lignes dans l'ordre d'affichage : titre en
        # premier, puis corps. L'attribut `id` est facultatif et parfois absent.
        blocks = [(node.text or "").strip() for node in root.iter("text")]
        blocks = [block for block in blocks if block]
        if not blocks:
            return "", "", ""

        title = blocks[0]
        body = " ".join(blocks[1:]) if len(blocks) > 1 else ""
        return title, "", body

    def app_name(self, identifier: str) -> str:
        return _readable_windows_name(identifier)


def _source_for(platform: str) -> _Source | None:
    """Adaptateur correspondant au système, `None` s'il n'est pas pris en charge."""
    if platform == "darwin":
        return _MacSource()
    if platform == "win32":
        return _WindowsSource()
    return None


class NotificationReader:
    """Lecture périodique des notifications, avec déduplication.

    Les notifications identiques répétées sont fusionnées : certaines
    applications en émettent plusieurs d'affilée, ce qui saturerait l'écran de
    la console.

    `ignored` permet d'écarter des applications par nom ou par identifiant.
    Aucune clé de configuration ne l'alimente aujourd'hui ; le paramètre existe
    pour que l'appelant puisse le faire.

    `source` sert aux tests, qui fournissent un adaptateur et une base
    synthétiques. Par défaut, le système courant décide.
    """

    def __init__(
        self,
        ignored: list[str] | None = None,
        source: _Source | None = None,
        path: Path | None = None,
    ) -> None:
        self._source = source if source is not None else _source_for(sys.platform)
        if path is not None:
            self.path = path
        elif self._source is not None:
            self.path = Path(os.path.expanduser(self._source.path))
        else:
            self.path = None

        self.available = self.path is not None and self.path.is_file()
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
        if not self.available or self.broken or self._source is None:
            return []

        rows = self._rows()
        if rows is None:
            return []

        now = time.time()
        results: list[Notification] = []
        seen: set[str] = set()

        for delivered, identifier, payload in rows:
            notification = self._decode(delivered, identifier or "", payload, now)
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

    def _rows(self) -> list[tuple] | None:
        """Lignes brutes de la base, ou `None` si elle est illisible."""
        try:
            # Ouverture en lecture seule : la base appartient au système et ne
            # doit sous aucun prétexte être modifiée.
            connection = sqlite3.connect(
                f"file:{self.path}?mode=ro", uri=True, timeout=1.0
            )
        except sqlite3.Error:
            self.broken = True
            return None

        try:
            return connection.execute(self._source.query).fetchall()
        except sqlite3.Error:
            # Schéma inattendu : la fonctionnalité s'éteint proprement plutôt
            # que de réessayer indéfiniment.
            self.broken = True
            return None
        finally:
            connection.close()

    def _decode(
        self, delivered: object, identifier: str, payload: object, now: float
    ) -> Notification | None:
        """Convertit une ligne de la base en notification affichable."""
        moment = self._source.timestamp(delivered)
        if moment is None:
            return None

        age = now - moment
        # Une date future trahit une horloge décalée ou une valeur illisible :
        # la garder ferait passer l'entrée pour la plus récente de toutes. Une
        # légère avance reste tolérée, le temps n'étant pas lu au même instant.
        if age < -_CLOCK_TOLERANCE:
            return None
        if age < 0.0:
            age = 0.0
        if age > MAX_AGE_SECONDS:
            return None

        title, subtitle, body = self._source.texts(payload)

        # Une notification sans titre ni corps n'apporte rien.
        if not title and not body:
            return None

        app = self._source.app_name(identifier)
        if self._is_ignored(app, identifier):
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
            bundle=identifier,
            key=f"{identifier}|{title}|{body}",
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

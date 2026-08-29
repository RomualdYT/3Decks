"""Briques du serveur, partagées par ses différentes responsabilités.

Ce module rassemble ce qui ne dépend pas de l'état du serveur : les constantes
du protocole, la traduction d'une photographie du poste en message, la
présentation des fenêtres, le cache de pochette et la connexion d'une console.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

# Indispensable en Python 3.9 : les annotations `X | None` des méthodes ne
# sont évaluées qu'à la demande grâce à cet import.
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from .. import artwork, palette, protocol
from ..config import MAX_BUTTONS_PER_PAGE, MAX_DETAIL, MAX_LABEL, MAX_LIST_ENTRIES, Action, ButtonConfig, ListEntry
from ..platforms.base import SystemSnapshot

VERSION = "0.1.0"
SETTLE_DELAY = 0.12
SLOW_CONFIRM_DELAY = 2.2
MAX_PAYLOAD_APPS = 8
MAX_PAYLOAD_AUDIO_OUTPUTS = 6
MAX_PAYLOAD_NOTIFICATIONS = 4
_MONTHS = (
    "janvier",
    "fevrier",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "aout",
    "septembre",
    "octobre",
    "novembre",
    "decembre",
)
_OPTIONAL_FIELDS = (
    "volume",
    "muted",
    "mic_muted",
    "app_volume",
    "cpu",
    "memory",
    "memory_used_mb",
    "memory_total_mb",
    "disk",
    "disk_free_mb",
    "disk_total_mb",
    "network_down_kbps",
    "network_up_kbps",
    "top_process_cpu",
    "gpu",
    "temperature",
)
def _snapshot_payload(snapshot: SystemSnapshot) -> dict[str, Any]:
    """Traduit une photographie du poste en message `state.update`."""
    now = datetime.now()

    payload: dict[str, Any] = {
        "type": "state.update",
        "time": now.strftime("%H:%M"),
        "date": f"{now.day} {_MONTHS[now.month - 1]}",
        "active_app": snapshot.active_app,
        "apps": snapshot.apps[:MAX_PAYLOAD_APPS],
    }

    for field_name in _OPTIONAL_FIELDS:
        value = getattr(snapshot, field_name)
        if value is not None:
            payload[field_name] = value

    if snapshot.top_process:
        payload["top_process"] = snapshot.top_process

    # La sortie audio est omise lorsqu'elle est vide, et non lorsqu'elle est
    # nulle : une chaîne vide ne désigne aucun périphérique.
    if snapshot.audio_output:
        payload["audio_output"] = snapshot.audio_output
    if snapshot.audio_outputs:
        payload["audio_outputs"] = snapshot.audio_outputs[:MAX_PAYLOAD_AUDIO_OUTPUTS]

    # La liste vide est significative : elle efface l'historique de la console
    # lorsque la dernière notification expire. Seules les entrées visibles sont
    # transmises ; le compteur conserve le total.
    payload["notifications"] = [
        item.as_payload()
        for item in snapshot.notifications[:MAX_PAYLOAD_NOTIFICATIONS]
    ]
    payload["notification_count"] = len(snapshot.notifications)

    if snapshot.new_notification is not None:
        # Signalée à part : la console l'annonce, quelle que soit la page.
        payload["notification_new"] = snapshot.new_notification.as_payload()

    # Une absence de média doit être annoncée : la console efface alors sa fiche
    # au lieu de conserver le morceau précédent.
    payload["media"] = (
        snapshot.media.as_payload() if snapshot.media is not None else None
    )
    return payload
class ArtworkCache:
    """Prépare et mémorise la pochette courante.

    La conversion coûte quelques dizaines de millisecondes et le transfert
    32 Ko : on ne refait donc le travail que lorsque l'adresse de la pochette
    change réellement.
    """

    def __init__(self) -> None:
        self._url = ""
        self._token = 0
        self._texture: bytes | None = None
        self._accent = ""

    @property
    def token(self) -> int:
        return self._token if self._texture is not None else 0

    @property
    def accent(self) -> str:
        """Couleur dominante de la pochette, au format `#RRGGBB`."""
        return self._accent

    def update(self, url: str) -> bool:
        """Prépare la pochette de `url`. Retourne `True` si elle a changé."""
        if not url:
            if self._texture is None and not self._url:
                return False
            self._url = ""
            self._token = 0
            self._texture = None
            self._accent = ""
            return True

        if url == self._url:
            return False

        self._url = url
        image = artwork.download(url)
        texture = artwork.to_texture(image) if image else None

        if texture is None:
            # Échec du téléchargement ou de la conversion : la console affichera
            # son substitut, ce qui reste préférable à une image erronée.
            self._texture = None
            self._token = 0
            self._accent = ""
            return True

        self._texture = texture
        self._token = artwork.token_for(url)

        # Couleur dominante : la console accorde son interface au morceau.
        colour = palette.dominant(texture)
        self._accent = palette.to_hex(colour) if colour else ""
        return True

    def payload(self) -> bytes | None:
        if self._texture is None:
            return None
        return artwork.frame(self._texture, self._token)
_APP_STYLES = {
    "safari": ("browser", "#3B82F6"),
    "chrome": ("browser", "#F59E0B"),
    "firefox": ("browser", "#F97316"),
    "arc": ("browser", "#1D4ED8"),
    "spotify": ("music", "#1DB954"),
    "music": ("music", "#FA57C1"),
    "discord": ("chat", "#5865F2"),
    "messages": ("chat", "#34D399"),
    "slack": ("chat", "#611F69"),
    "terminal": ("terminal", "#94A3B8"),
    "iterm": ("terminal", "#6B7280"),
    "code": ("app", "#0EA5E9"),
    "finder": ("folder", "#FBBF24"),
    "notes": ("page", "#FCD34D"),
    "calendrier": ("page", "#EF4444"),
    "calendar": ("page", "#EF4444"),
}
_DEFAULT_STYLE = ("app", "#64748B")
def _icon_for(app: str) -> tuple[str, str]:
    """Icône et couleur d'une application, avec un repli neutre."""
    lowered = app.lower()
    for needle, style in _APP_STYLES.items():
        if needle in lowered:
            return style
    return _DEFAULT_STYLE
def _window_entries(
    windows: list[tuple[str, str]], active_app: str = ""
) -> list[ListEntry]:
    """Construit les éléments de liste correspondant aux fenêtres ouvertes.

    L'ordre reçu est conservé : il correspond à l'empilement des fenêtres, donc
    à l'usage le plus récent, ce qui place naturellement en tête ce que
    l'utilisateur vient de quitter.

    Le premier élément de l'application au premier plan est marqué comme actif,
    afin que la console puisse le mettre en évidence.
    """
    entries: list[ListEntry] = []
    active_marked = False

    for index, (app, title) in enumerate(windows[:MAX_LIST_ENTRIES]):
        icon, colour = _icon_for(app)

        # Un détail identique au nom de l'application n'apporte rien.
        detail = ""
        if title and title.strip().lower() != app.strip().lower():
            detail = title[:MAX_DETAIL]

        is_active = (
            not active_marked
            and bool(active_app)
            and app.strip().lower() == active_app.strip().lower()
        )
        if is_active:
            active_marked = True

        entries.append(
            ListEntry(
                id=f"win-{index}",
                label=app[: MAX_LABEL - 1],
                detail=detail,
                icon=icon,
                color=colour,
                active=is_active,
                action=Action("window.focus", {"app": app, "title": title}),
            )
        )

    return entries
def _window_buttons(windows: list[tuple[str, str]]) -> list[ButtonConfig]:
    """Construit les boutons correspondant aux fenêtres ouvertes.

    Les libellés privilégient le nom de l'application, plus court et plus
    reconnaissable sur un petit écran, et le titre de la fenêtre sert d'indice
    secondaire pour distinguer deux fenêtres d'une même application.
    """
    buttons: list[ButtonConfig] = []

    for slot, (app, title) in enumerate(windows[:MAX_BUTTONS_PER_PAGE]):
        icon, colour = _icon_for(app)

        # Un titre identique au nom de l'application n'apporte rien.
        hint = ""
        if title and title.strip().lower() != app.strip().lower():
            hint = title

        buttons.append(
            ButtonConfig(
                id=f"win-{slot}",
                slot=slot,
                # Un nom d'application n'a pas de traduction : la même valeur
                # sert pour toutes les langues.
                labels={
                    locale: app[: MAX_LABEL - 1] for locale in ("en", "fr")
                },
                icon=icon,
                color=colour,
                hold_labels=(
                    {locale: hint[: MAX_LABEL - 1] for locale in ("en", "fr")}
                    if hint
                    else {}
                ),
                action=Action("window.focus", {"app": app, "title": title}),
            )
        )

    return buttons
class Client:
    """Une console connectée."""

    _counter = 0

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        Client._counter += 1
        self.id = Client._counter
        self.reader = reader
        self.writer = writer
        self.reader_state = protocol.FrameReader()
        self.authenticated = False
        # Vrai uniquement pour le handshake ayant consommé le code court. Le
        # jeton durable est alors renvoyé une fois à cette console.
        self.paired_now = False
        # La langue appartient à la console, pas au serveur. Deux consoles
        # peuvent ainsi recevoir simultanément leurs propres libellés.
        self.language = "en"
        self.address = "?"

        peer = writer.get_extra_info("peername")
        if peer:
            self.address = f"{peer[0]}:{peer[1]}"

    async def _write(self, frame: bytes) -> bool:
        """Écrit une trame déjà encodée.

        Retourne `False` si la connexion est perdue, ce qui conduit l'appelant à
        retirer cette console.
        """
        try:
            self.writer.write(frame)
            await self.writer.drain()
            return True
        except (ConnectionError, OSError):
            return False

    async def send(self, message: dict[str, Any]) -> bool:
        """Envoie un message. Retourne `False` si la connexion est perdue."""
        try:
            frame = protocol.encode(message)
        except protocol.ProtocolError:
            # Message impossible à encoder : la faute est de notre côté, la
            # console reste jointe. La retirer masquerait le vrai défaut.
            return True
        return await self._write(frame)

    async def send_raw(self, payload: bytes) -> bool:
        """Envoie une charge utile binaire, en y ajoutant l'en-tête de longueur."""
        try:
            frame = protocol.encode_raw(payload)
        except protocol.ProtocolError:
            return True
        return await self._write(frame)

    async def close(self) -> None:
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except (ConnectionError, OSError):
            pass
@dataclass
class Options:
    """Réglages de déploiement du serveur.

    Ils décrivent la façon de lancer l'agent, non son comportement vis-à-vis de
    la console : les regrouper évite d'allonger la signature du constructeur à
    chaque nouvelle option, et permet de les transmettre d'un bloc.
    """

    #: Journalisation détaillée sur la sortie standard.
    verbose: bool = False
    #: Fichier surveillé pour le rechargement à chaud. `None` le désactive.
    config_path: Path | None = None
    #: Port de l'interface de configuration. `None` la désactive.
    ui_port: int | None = None

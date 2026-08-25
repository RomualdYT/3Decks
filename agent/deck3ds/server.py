"""Serveur TCP de l'agent Deck3DS.

Le serveur accepte plusieurs consoles simultanément, diffuse l'état du poste et
exécute les actions demandées. La collecte d'état, qui repose sur des appels
système parfois lents, est déportée dans un fil d'exécution afin de ne jamais
bloquer la boucle d'événements.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import asyncio
import platform as platform_module
import socket
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from . import artwork, messages, palette, protocol
from . import config as config_module
from .actions import Dispatcher
from .config import (
    MAX_BUTTONS_PER_PAGE,
    MAX_DETAIL,
    MAX_LABEL,
    MAX_LIST_ENTRIES,
    Action,
    ButtonConfig,
    Config,
    ListEntry,
)
from .platforms.base import Platform, SystemSnapshot

VERSION = "0.1.0"

#: Délai laissé au système pour appliquer une commande avant de la mesurer.
#: Sans lui, la relecture immédiate rapporterait encore l'ancienne valeur.
SETTLE_DELAY = 0.12

#: Attente supplémentaire pour les commandes à effet différé (changement de
#: piste, bascule de sortie audio). Mesuré sur une diffusion Spotify vers une
#: enceinte externe : l'état de lecture met environ deux secondes à changer.
SLOW_CONFIRM_DELAY = 2.2

#: Bornes de troncature du message d'état. La console n'affiche pas davantage,
#: et chaque valeur transmise coûte de la bande passante à chaque cycle.
MAX_PAYLOAD_APPS = 8
MAX_PAYLOAD_AUDIO_OUTPUTS = 6
#: Aligné sur `MAX_NOTIFICATIONS` de `3ds-app/source/model.h` : la console ne
#: réserve que quatre emplacements. Le total réel voyage séparément, dans
#: `notification_count`, qui alimente le badge de l'écran supérieur.
MAX_PAYLOAD_NOTIFICATIONS = 4

#: Mois en français, pour éviter de dépendre de la locale du système.
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


#: Champs omis lorsqu'ils valent `None`. La console conserve alors ce qu'elle
#: sait déjà, plutôt que d'afficher une donnée fausse.
_OPTIONAL_FIELDS = ("volume", "muted", "mic_muted", "app_volume", "cpu", "memory")


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

    # La sortie audio est omise lorsqu'elle est vide, et non lorsqu'elle est
    # nulle : une chaîne vide ne désigne aucun périphérique.
    if snapshot.audio_output:
        payload["audio_output"] = snapshot.audio_output
    if snapshot.audio_outputs:
        payload["audio_outputs"] = snapshot.audio_outputs[:MAX_PAYLOAD_AUDIO_OUTPUTS]

    if snapshot.notifications:
        # Seules les plus récentes sont transmises ; `notification_count`
        # indique le total, que la console affiche sous forme de compteur.
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


#: Présentation des applications courantes dans la liste des fenêtres :
#: icône et couleur déclarées ensemble. Deux tables séparées laissaient six
#: applications avec une icône mais sans couleur — Slack, Arc et iTerm
#: retombaient sur le gris de repli alors que leur icône était bien définie.
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

#: Repli lorsqu'aucune correspondance n'est trouvée.
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


class Server:
    def __init__(
        self,
        config: Config,
        platform: Platform,
        options: Options | None = None,
    ):
        options = options or Options()
        self.config = config
        #: Fichier de configuration surveillé, pour un rechargement à chaud.
        self.config_path = options.config_path
        self._config_mtime = self._config_stamp()
        self.platform = platform
        self.dispatcher = Dispatcher(platform, config)
        self.verbose = options.verbose

        self.clients: set[Client] = set()
        self._last_payload: dict[str, Any] | None = None
        # Créé à l'entrée dans la boucle, pas ici : jusqu'à Python 3.9,
        # `asyncio.Event()` se lie à la boucle d'événements courante lors de sa
        # construction. Le serveur étant instancié avant `asyncio.run`, l'objet
        # se rattachait à une boucle absente puis inexistante, et le premier
        # `wait()` levait « attached to a different loop ». La boucle de
        # collecte mourait alors sans bruit : plus de rechargement à chaud, plus
        # de rafraîchissement de l'état, et un écran figé sur la console.
        self._refresh_event: asyncio.Event | None = None
        self._server: asyncio.base_events.Server | None = None
        self._artwork = ArtworkCache()
        #: Demande une seconde lecture différée, pour les commandes dont l'effet
        #: met plusieurs secondes à devenir visible.
        self._slow_confirm = False
        #: Fenêtres publiées lors du dernier envoi de configuration, pour
        #: n'émettre une nouvelle configuration que si la liste a changé.
        self._published_windows: list[tuple[str, str]] = []
        #: Journal récent, borné : l'interface l'affiche, et une exécution de
        #: plusieurs jours ne doit pas consommer de mémoire sans fin.
        self._logs: deque[str] = deque(maxlen=300)
        #: Version exposée à l'interface, sans qu'elle importe ce module.
        self.version = VERSION
        #: Port de l'interface de configuration, `None` si désactivée.
        self.ui_port = options.ui_port
        self._ui: Any | None = None
        #: Appelée avec l'URL de l'interface dès qu'elle écoute. Permet au point
        #: d'entrée d'ouvrir le navigateur sans que le serveur en dépende.
        self.on_ui_ready: Callable[[str], None] | None = None

    def _wake(self) -> asyncio.Event:
        """Signal de rafraîchissement, créé à la première utilisation.

        Voir le commentaire du constructeur : la création doit avoir lieu dans
        la boucle qui l'attend.
        """
        if self._refresh_event is None:
            self._refresh_event = asyncio.Event()
        return self._refresh_event

    def _config_stamp(self) -> float:
        """Date de modification du fichier de configuration, 0 si indisponible."""
        if self.config_path is None:
            return 0.0
        try:
            return self.config_path.stat().st_mtime
        except OSError:
            return 0.0

    def reload_config_if_changed(self) -> bool:
        """Recharge la configuration si le fichier a été modifié.

        Sans cela, un agent démarré avant une modification continuerait de
        servir l'ancienne mise en page : le fichier semblerait à jour alors que
        la console recevrait une version périmée. C'est une source de confusion
        difficile à diagnostiquer.
        """
        if self.config_path is None:
            return False

        stamp = self._config_stamp()
        if stamp == 0.0 or stamp == self._config_mtime:
            return False

        self._config_mtime = stamp

        try:
            loaded = config_module.load(self.config_path)
        except config_module.ConfigError as error:
            # Une erreur de saisie ne doit pas interrompre le service : on
            # signale et on conserve la configuration en cours.
            self.log(f"Configuration invalide, ancienne version conservee : {error}")
            return False

        self.config = loaded
        self.dispatcher.set_config(loaded)
        self._published_windows = []
        self.log(f"Configuration rechargee ({len(loaded.pages)} pages)")
        return True

    def _has_dynamic_pages(self) -> bool:
        return any(page.source == "windows" for page in self.config.pages)

    def _fill_dynamic_pages(
        self, windows: list[tuple[str, str]], active_app: str = ""
    ) -> None:
        """Remplit les pages alimentées automatiquement.

        Selon la présentation choisie, la page reçoit soit une liste défilante,
        soit une grille limitée à six boutons.
        """
        for page in self.config.pages:
            if page.source != "windows":
                continue

            if page.layout == "list":
                page.entries = _window_entries(windows, active_app)
            else:
                page.buttons = _window_buttons(windows)

        # Le dispatcher partage la configuration : il retrouvera ainsi les
        # boutons générés lors de la résolution d'un appui.
        self.dispatcher.set_config(self.config)
        self._published_windows = list(windows)

    def _config_message(self) -> dict[str, Any]:
        """Configuration à transmettre, pages dynamiques comprises.

        La révision est décalée du nombre de fenêtres afin que la console
        distingue deux configurations dont seules les pages dynamiques diffèrent.
        """
        payload = self.config.snapshot_payload(messages.language())
        if self._has_dynamic_pages():
            payload["revision"] = (
                self.config.revision * 1000 + len(self._published_windows)
            )
        return payload

    # --- Journalisation -------------------------------------------------------

    def log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        # Conservé avant l'affichage : l'interface montre les mêmes lignes que
        # la console, sans avoir à détourner la sortie standard.
        self._logs.append(f"[{stamp}] {message}")
        print(f"[{stamp}] {message}", flush=True)

    def debug(self, message: str) -> None:
        if self.verbose:
            self.log(message)

    def recent_logs(self) -> list[str]:
        """Dernières lignes journalisées, de la plus ancienne à la plus récente."""
        return list(self._logs)

    def last_state_payload(self) -> dict[str, Any]:
        """Dernier état diffusé, ou un objet vide si rien n'a encore circulé.

        L'interface s'en sert pour afficher volume, média et sortie audio sans
        provoquer de nouvelle collecte.

        La copie est profonde d'un niveau : une copie superficielle laisserait
        `media` partagé avec l'état vivant du serveur, que la collecte mute pour
        y placer le jeton de pochette.
        """
        payload = self._last_payload or {}
        return {
            key: dict(value) if isinstance(value, dict) else value
            for key, value in payload.items()
        }

    # --- Cycle de vie ---------------------------------------------------------

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client,
            self.config.host,
            self.config.port,
            reuse_address=True,
        )

        addresses = ", ".join(
            f"{sock.getsockname()[0]}:{sock.getsockname()[1]}"
            for sock in self._server.sockets
        )
        self.log(f"Agent Deck3DS {VERSION} en ecoute sur {addresses}")

        for hint in self.local_addresses():
            self.log(f"  adresse a saisir sur la 3DS : {hint}")

        if not self.config.token:
            self.log("  aucun jeton configure : toute console du reseau peut agir")

        await self._start_ui()

        poller = asyncio.create_task(self._poll_loop())

        try:
            async with self._server:
                await self._server.serve_forever()
        except asyncio.CancelledError:
            pass
        finally:
            poller.cancel()
            for client in list(self.clients):
                await client.close()
            if self._ui is not None:
                await self._ui.close()

    async def _start_ui(self) -> None:
        """Démarre l'interface de configuration, si elle est demandée.

        Un échec n'interrompt pas l'agent : un port déjà pris ne doit pas priver
        la console de sa surface de contrôle, qui reste la fonction première.
        """
        if self.ui_port is None:
            return

        # Import différé : l'agent démarre sans l'interface si elle n'est pas
        # utilisée, et le module d'interface peut importer le serveur.
        from .ui.api import Api
        from .ui.http import UiServer

        api = Api(self)
        ui = UiServer(api.routes(), port=self.ui_port, log=self.log)

        try:
            await ui.start()
        except OSError as error:
            self.log(f"Interface indisponible sur le port {self.ui_port} : {error}")
            return

        self._ui = ui

        if self.on_ui_ready is not None:
            try:
                self.on_ui_ready(ui.url)
            except Exception as error:  # ouvrir le navigateur reste accessoire
                self.debug(f"ouverture du navigateur impossible : {error}")

    def local_addresses(self) -> list[str]:
        """Devine les adresses utilisables, pour éviter à l'utilisateur de
        chercher son IP à la main."""
        found: list[str] = []
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Aucune donnée n'est envoyée : cela sert seulement à déterminer
            # l'interface qu'emprunterait une connexion sortante.
            probe.connect(("8.8.8.8", 80))
            found.append(f"{probe.getsockname()[0]}:{self.config.port}")
            probe.close()
        except OSError:
            pass
        return found

    # --- Diffusion ------------------------------------------------------------

    def _audience(self) -> list[Client]:
        """Consoles autorisées à recevoir un message.

        La liste est copiée : une console peut être retirée pendant l'envoi,
        ce qui invaliderait un parcours direct de l'ensemble.
        """
        return [client for client in list(self.clients) if client.authenticated]

    async def _broadcast(self, message: dict[str, Any]) -> None:
        """Envoie un message à toutes les consoles authentifiées.

        Une console injoignable est retirée : sans cela, chaque cycle
        réessaierait indéfiniment d'écrire dans une socket fermée.
        """
        for client in self._audience():
            if not await client.send(message):
                await self._drop(client)

    async def _drop(self, client: Client) -> None:
        """Retire une console dont la connexion est perdue."""
        self.clients.discard(client)
        await client.close()

    # --- Connexions -----------------------------------------------------------

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        client = Client(reader, writer)
        self.clients.add(client)
        self.log(f"Console #{client.id} connectee depuis {client.address}")

        try:
            await self._read_messages(client, reader)
        except (ConnectionError, OSError):
            pass
        finally:
            self.clients.discard(client)
            await client.close()
            self.log(f"Console #{client.id} deconnectee")

    async def _dispatch_available(self, client: Client) -> bool:
        """Traite les messages complets déjà reçus.

        Retourne `False` si une trame invalide impose de couper la connexion :
        le flux est alors désynchronisé et rien ne permet de s'y resynchroniser.
        """
        try:
            for message in client.reader_state:
                await self._handle_message(client, message)
        except protocol.ProtocolError as error:
            self.log(f"Console #{client.id}: trame invalide ({error})")
            return False
        return True

    async def _read_messages(
        self, client: Client, reader: asyncio.StreamReader
    ) -> None:
        """Lit le flux d'une console jusqu'à sa fermeture."""
        while True:
            data = await reader.read(8192)
            if not data:
                return

            client.reader_state.feed(data)
            if not await self._dispatch_available(client):
                return

    async def _handle_config_request(
        self, client: Client, message: dict[str, Any]
    ) -> None:
        """Renvoie la mise en page, puis l'état courant s'il existe."""
        await client.send(self._config_message())
        if self._last_payload is not None:
            await client.send(self._last_payload)

    async def _handle_ping(self, client: Client, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        await client.send(
            protocol.pong(request_id if isinstance(request_id, int) else 0)
        )

    async def _handle_message(self, client: Client, message: dict[str, Any]) -> None:
        kind = message.get("type")

        if kind == "hello":
            await self._handle_hello(client, message)
            return

        # Tout le reste exige un handshake réussi.
        if not client.authenticated:
            self.debug(f"Console #{client.id}: message avant handshake ({kind})")
            return

        # Table de routage plutôt qu'une chaîne de comparaisons : ajouter un
        # message se voit d'un coup d'œil, et un type inconnu ne peut pas être
        # confondu avec un oubli de branche.
        handlers = {
            "button.press": self._handle_button,
            "value.set": self._handle_value,
            "config.request": self._handle_config_request,
            "ping": self._handle_ping,
        }
        handler = handlers.get(kind)
        if handler is None:
            self.debug(f"Console #{client.id}: type ignore ({kind})")
            return
        await handler(client, message)

    async def _reject_handshake(self, client: Client, reason: str, note: str) -> None:
        """Refuse une console et ferme la connexion."""
        await client.send(protocol.hello_error(reason))
        self.log(f"Console #{client.id}: {note}")
        await client.close()

    async def _accept_handshake(self, client: Client, message: dict[str, Any]) -> bool:
        """Vérifie la version du protocole et le jeton.

        Retourne `False` si la console a été refusée ; la réponse est alors déjà
        émise et la connexion fermée.
        """
        version = message.get("protocol")
        if version != protocol.PROTOCOL_VERSION:
            await self._reject_handshake(
                client,
                f"protocole {version}, attendu {protocol.PROTOCOL_VERSION}",
                "version de protocole incompatible",
            )
            return False

        # Comparaison simple : le jeton protège d'un usage accidentel sur le
        # réseau local, il ne prétend pas résister à une analyse temporelle.
        if self.config.token and message.get("token") != self.config.token:
            await self._reject_handshake(client, "jeton invalide", "jeton refuse")
            return False

        return True

    async def _send_initial_state(self, client: Client) -> None:
        """Met la console à niveau juste après son acceptation.

        Une console qui vient d'arriver ne possède aucune pochette : celle en
        cours lui est transmise même si elle n'a pas changé.
        """
        if self._last_payload is None:
            # Première console connectée : une collecte immédiate évite de
            # laisser le tableau de bord vide.
            self._wake().set()
            return

        await client.send(self._last_payload)
        art = self._artwork.payload()
        if art is not None:
            await client.send_raw(art)

    async def _handle_hello(self, client: Client, message: dict[str, Any]) -> None:
        if not await self._accept_handshake(client, message):
            return

        # La console indique sa langue : les notifications renvoyées suivront.
        messages.set_language(str(message.get("language", "en")))
        client.authenticated = True

        # Première console : les pages dynamiques ne sont pas encore remplies.
        # Les alimenter avant d'envoyer la configuration évite une page vide.
        if self._has_dynamic_pages() and not self._published_windows:
            windows = await asyncio.to_thread(self.platform.list_windows)
            active = await asyncio.to_thread(self.platform.get_active_app)
            self._fill_dynamic_pages(windows, active)

        await client.send(
            protocol.hello_ok(
                VERSION, platform_module.node() or "PC", self.platform.name
            )
        )
        await client.send(self._config_message())
        await self._send_initial_state(client)

        self.log(f"Console #{client.id}: handshake accepte")

    async def _handle_value(self, client: Client, message: dict[str, Any]) -> None:
        """Applique un réglage continu venu d'un curseur.

        Les curseurs transmettent la valeur voulue plutôt qu'une succession
        d'incréments : un seul message suffit là où les boutons plus et moins en
        demandaient une dizaine.
        """
        request_id = message.get("id")
        if not isinstance(request_id, int):
            request_id = 0

        target = message.get("target")
        value = message.get("value")

        if not isinstance(target, str) or not isinstance(value, int):
            await client.send(
                protocol.action_result(request_id, False, "requete invalide")
            )
            return

        # Seuls les réglages continus connus sont acceptés : la console ne peut
        # pas désigner une propriété arbitraire.
        allowed = {"volume": "volume.set", "app_volume": "app_volume.set"}
        kind = allowed.get(target)

        if kind is None:
            await client.send(
                protocol.action_result(request_id, False, "reglage inconnu")
            )
            return

        outcome = await asyncio.to_thread(
            self.dispatcher.run, Action(kind, {"value": value})
        )

        await client.send(
            protocol.action_result(request_id, outcome.ok, outcome.message)
        )

        if outcome.state_changed:
            self._wake().set()

    async def _resolve_target(
        self, client: Client, request_id: int, page_id: str, button_id: str
    ):
        """Retrouve ce qu'un appui désigne, ou refuse la demande.

        Trois provenances sont possibles : un bouton de la configuration, un
        élément de liste — qui emprunte le même message que la grille — ou un
        panneau de la console, qui envoie directement un nom d'action.

        Retourne `(bouton, action)` dont au plus un est renseigné, ou `None` si
        la demande a été refusée et la réponse déjà émise.
        """
        if page_id == "__direct":
            # La console transmet le nom de l'action. Seules celles de la liste
            # blanche sont acceptées, comme partout ailleurs.
            if button_id not in config_module.KNOWN_ACTIONS:
                await client.send(
                    protocol.action_result(request_id, False, "action inconnue")
                )
                self.log(f"Console #{client.id}: action refusee {button_id}")
                return None
            return None, Action(button_id, {})

        button = self.config.find_button(page_id, button_id)
        if button is not None:
            return button, None

        action = self.config.find_action(page_id, button_id)
        if action is None:
            await client.send(
                protocol.action_result(request_id, False, "bouton inconnu")
            )
            self.log(f"Console #{client.id}: element inconnu {page_id}/{button_id}")
            return None
        return None, action

    async def _run_action(self, button, action, hold: bool):
        """Exécute l'action demandée et mesure sa durée.

        L'exécution peut appeler AppleScript ou PowerShell : elle est déportée
        dans un fil pour que la boucle d'événements reste réactive.
        """
        started = time.monotonic()
        if button is not None:
            outcome = await asyncio.to_thread(
                self.dispatcher.run_button, button, hold
            )
        else:
            outcome = await asyncio.to_thread(self.dispatcher.run, action)
        return outcome, (time.monotonic() - started) * 1000.0

    def _schedule_confirmation(self, outcome) -> None:
        """Provoque une collecte immédiate lorsque l'action a modifié le poste.

        Sans elle, l'écran conserverait l'ancien état jusqu'au cycle suivant et
        le bouton semblerait sans effet.
        """
        if not outcome.state_changed:
            return
        if outcome.slow_effect:
            self._slow_confirm = True
        self._wake().set()

    async def _handle_button(self, client: Client, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        if not isinstance(request_id, int):
            request_id = 0

        page_id = message.get("page")
        button_id = message.get("button")
        hold = bool(message.get("hold", False))

        if not isinstance(page_id, str) or not isinstance(button_id, str):
            await client.send(
                protocol.action_result(request_id, False, "requete invalide")
            )
            return

        target = await self._resolve_target(client, request_id, page_id, button_id)
        if target is None:
            return

        button, action = target
        outcome, elapsed = await self._run_action(button, action, hold)

        status = "ok" if outcome.ok else "echec"
        self.log(
            f"Console #{client.id}: {page_id}/{button_id}"
            f"{' (long)' if hold else ''} -> {status}"
            f" [{elapsed:.0f} ms]"
            + (f" {outcome.message}" if outcome.message else "")
        )

        await client.send(
            protocol.action_result(
                request_id,
                outcome.ok,
                outcome.message,
                outcome.open_page,
                outcome.open_settings,
                outcome.open_modal,
                outcome.toggle_frame,
            )
        )
        self._schedule_confirmation(outcome)

    async def _poll_loop(self) -> None:
        try:
            await self._poll_forever()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            # Sans cette trace, une panne de la boucle passait inaperçue : la
            # tâche mourait, plus rien ne se rafraîchissait, et l'agent semblait
            # fonctionner puisqu'il répondait toujours aux appuis. Un tel silence
            # coûte des heures de diagnostic.
            self.log(
                f"Collecte interrompue : {type(error).__name__}: {error}. "
                "L'etat ne sera plus rafraichi, redemarrez l'agent."
            )
            raise

    async def _collect_safely(self) -> None:
        """Collecte l'état sans jamais laisser une panne arrêter la boucle."""
        try:
            await self._refresh_state()
        except Exception as error:  # la boucle ne doit jamais s'arrêter
            self.debug(f"collecte en echec: {type(error).__name__}: {error}")

    async def _wait_for_wake(self) -> bool:
        """Attend un réveil ou l'expiration de l'intervalle de collecte.

        Retourne `True` si une action a demandé un rafraîchissement immédiat.
        """
        try:
            await asyncio.wait_for(
                self._wake().wait(), timeout=self.config.poll_interval
            )
        except asyncio.TimeoutError:
            return False
        self._wake().clear()
        return True

    async def _confirm_after_action(self) -> None:
        """Relit l'état après une action, une fois le système stabilisé.

        Une lecture immédiate rapporterait encore l'ancienne valeur. Certaines
        commandes demandent bien davantage : une diffusion Spotify vers une
        enceinte externe met environ deux secondes à changer l'état de lecture,
        d'où la seconde relecture différée.

        Ces relectures ne sont pas protégées, contrairement à la collecte
        périodique : une panne survenant ici doit remonter jusqu'à `_poll_loop`,
        qui la journalise. La masquer priverait du diagnostic.
        """
        await asyncio.sleep(SETTLE_DELAY)
        await self._refresh_state()

        if not self._slow_confirm:
            return
        self._slow_confirm = False
        await asyncio.sleep(SLOW_CONFIRM_DELAY)
        await self._refresh_state()

    async def _poll_forever(self) -> None:
        while True:
            # Le fichier de configuration est relu si nécessaire avant chaque
            # collecte : une modification est ainsi appliquée en quelques
            # secondes, sans redémarrer l'agent.
            if self.reload_config_if_changed():
                await self._broadcast(self._config_message())

            await self._collect_safely()

            if await self._wait_for_wake():
                await self._confirm_after_action()

    async def _refresh_state(self) -> None:
        """Collecte l'état du poste et diffuse ce qui a changé.

        Chaque étape est isolée : la collecte, la remise à jour des pages
        dynamiques, la pochette, puis la diffusion du différentiel.
        """
        if not self.clients:
            # Personne n'écoute : inutile de solliciter le système.
            return

        snapshot = await asyncio.to_thread(self.platform.snapshot)
        payload = _snapshot_payload(snapshot)

        await self._republish_windows(snapshot.active_app)
        art = await self._refresh_artwork(snapshot, payload)
        await self._publish(self._delta_since_last(payload), art)

    async def _republish_windows(self, active_app: str) -> None:
        """Reconstruit les pages alimentées automatiquement, si nécessaire.

        La configuration n'est renvoyée que lorsque la liste des fenêtres a
        réellement changé : sinon la console rebâtirait son interface à chaque
        seconde.
        """
        if not self._has_dynamic_pages():
            return

        windows = await asyncio.to_thread(self.platform.list_windows)
        if windows == self._published_windows:
            return

        self._fill_dynamic_pages(windows, active_app)
        await self._broadcast(self._config_message())

    async def _refresh_artwork(
        self, snapshot: SystemSnapshot, payload: dict[str, Any]
    ) -> bytes | None:
        """Prépare la pochette et complète le message d'état.

        Téléchargement et conversion se font dans un fil : ils ne doivent pas
        retarder la boucle d'événements. Le jeton permet à la console d'ignorer
        une image qu'elle possède déjà.

        Retourne la charge binaire à transmettre, ou `None` si rien n'a changé.
        """
        art_url = snapshot.media.art_url if snapshot.media is not None else ""
        changed = await asyncio.to_thread(self._artwork.update, art_url)

        media = payload.get("media")
        if isinstance(media, dict) and self._artwork.token:
            media["art"] = self._artwork.token
            if self._artwork.accent:
                media["accent"] = self._artwork.accent

        return self._artwork.payload() if changed else None

    def _delta_since_last(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Champs modifiés depuis la dernière diffusion.

        N'émettre que les différences limite le trafic et le travail de la
        console. Le type est toujours conservé : il identifie le message.
        """
        previous = self._last_payload
        self._last_payload = payload

        if previous is None:
            return payload
        return {
            key: value
            for key, value in payload.items()
            if key == "type" or previous.get(key) != value
        }

    async def _publish(self, delta: dict[str, Any], art: bytes | None) -> None:
        """Transmet le différentiel, puis la pochette si elle a changé."""
        # Un différentiel réduit au seul type n'annonce aucun changement.
        has_change = len(delta) > 1
        if not has_change and art is None:
            return

        for client in self._audience():
            if has_change and not await client.send(delta):
                await self._drop(client)
                continue
            if art is not None:
                await client.send_raw(art)

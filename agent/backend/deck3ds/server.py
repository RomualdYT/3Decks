"""Serveur TCP de l'agent Deck3DS.

Une console se connecte, s'annonce, reçoit la mise en page puis un flux d'états.
Elle renvoie les appuis, que l'agent exécute sur le poste.

La classe `Server` assemble des responsabilités déclarées séparément dans
`deck3ds.srv` : journalisation, diffusion, surveillance de la configuration,
collecte de l'état, commandes, accueil d'une console, connexions et cycle de
vie. Chacune se lit isolément ; l'état partagé est déclaré ici, en un seul
endroit, ce qui reste la référence pour savoir ce qu'un mixin peut utiliser.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Callable

from .actions import Dispatcher
from .config import Config
from .pairing import PairingManager
from .platforms.base import Platform
from .srv.broadcast import BroadcastMixin
from .srv.collect import CollectMixin
from .srv.commands import CommandMixin
from .srv.configwatch import ConfigWatchMixin
from .srv.connection import ConnectionMixin
from .srv.discovery import DiscoveryMixin
from .srv.handshake import HandshakeMixin
from .srv.lifecycle import LifecycleMixin
from .srv.logs import LoggingMixin

# Réexportés : l'interface de configuration et les tests les désignent par ce
# module, qui reste le point d'entrée du serveur.
from .srv.parts import (  # noqa: F401
    _APP_STYLES,
    _DEFAULT_STYLE,
    _icon_for,
    _snapshot_payload,
    _window_buttons,
    _window_entries,
    ArtworkCache,
    Client,
    Options,
    VERSION,
)


class Server(
    LoggingMixin,
    BroadcastMixin,
    ConfigWatchMixin,
    CollectMixin,
    CommandMixin,
    HandshakeMixin,
    ConnectionMixin,
    DiscoveryMixin,
    LifecycleMixin,
):
    """Serveur de l'agent : un état partagé, des responsabilités assemblées."""

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
        self.platform.configure_features(config.features)
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
        self._discovery_transport: asyncio.DatagramTransport | None = None
        self.pairing = PairingManager()
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

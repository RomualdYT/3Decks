"""Chargement et validation de la configuration.

La configuration décrit les pages, les boutons et l'action associée à chacun.
Elle est validée en profondeur : la 3DS ne doit jamais recevoir une structure
incohérente, et un fichier mal écrit doit produire un message clair plutôt
qu'une interface vide.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..action_catalog import ACTION_SPECS
from ..feature_catalog import FEATURE_SPECS as FEATURE_SPECS
from ..icon_catalog import ICONS as ICONS

#: Bornes alignées sur les limites de l'application 3DS.
MAX_PAGES = 12
MAX_BUTTONS_PER_PAGE = 6
#: Éléments transmis pour une page en mode liste. La console défile au-delà de
#: ce qui tient à l'écran.
MAX_LIST_ENTRIES = 32
#: Longueur de la ligne secondaire d'un élément de liste.
MAX_DETAIL = 40
MAX_LABEL = 24
MAX_ID = 32

#: Bornes des réglages numériques, sous forme `(minimum, maximum)`. Nommées ici
#: pour que la validation et l'interface partagent la même règle : l'éditeur les
#: recopiait, et rien ne garantissait qu'elles restent identiques.
#: Couleur d'un bouton dont la configuration n'en précise aucune.
DEFAULT_BUTTON_COLOR = "#3B82F6"

PORT_RANGE = (1, 65535)
POLL_INTERVAL_RANGE = (0.2, 30.0)
VOLUME_STEP_RANGE = (1, 50)
OBS_TIMEOUT_RANGE = (0.2, 15.0)

#: Vues de compatibilité dérivées du catalogue unique. Toute autre action est
#: rejetée : la console ne peut donc pas déclencher d'exécution arbitraire.
KNOWN_ACTIONS = frozenset(ACTION_SPECS)
ACTION_REQUIRED_ARG = {
    kind: next(argument.name for argument in spec.arguments if argument.required)
    for kind, spec in ACTION_SPECS.items()
    if any(argument.required for argument in spec.arguments)
}
ACTION_CAPABILITY = {
    kind: spec.capability
    for kind, spec in ACTION_SPECS.items()
    if spec.capability is not None
}


def action_arguments(kind: str) -> list[dict[str, Any]]:
    """Champs configurables d'une action, issus du catalogue partagé."""
    spec = ACTION_SPECS.get(kind)
    return (
        [] if spec is None else [argument.as_payload() for argument in spec.arguments]
    )


#: Capacité exigée par chaque tableau de bord, même logique que ci-dessus.
DASHBOARD_CAPABILITY = {
    "media": "media",
    "apps": "windows",
    "audio": "audio_output",
    "notifications": "notifications",
    "system": "system_stats",
    "frame": "media_artwork",
}

#: Modes de tableau de bord acceptés.
DASHBOARDS = {
    "auto",
    "media",
    "system",
    "apps",
    "audio",
    "frame",
    "notifications",
}


class ConfigError(Exception):
    """Configuration invalide."""


@dataclass
class Action:
    kind: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ButtonConfig:
    id: str
    slot: int
    #: Libellé par langue. Une même valeur pour toutes si non traduit.
    labels: dict[str, str] = field(default_factory=dict)
    icon: str = "app"
    color: str = DEFAULT_BUTTON_COLOR
    toggle: str = ""
    hold_labels: dict[str, str] = field(default_factory=dict)
    action: Action = field(default_factory=lambda: Action("noop"))
    hold_action: Action | None = None

    def label(self, locale: str = "en") -> str:
        return self.labels.get(locale) or self.labels.get("en", "")

    def hold_label(self, locale: str = "en") -> str:
        return self.hold_labels.get(locale) or self.hold_labels.get("en", "")

    def as_payload(self, locale: str = "en") -> dict[str, Any]:
        """Représentation envoyée à la 3DS, sans les détails d'exécution.

        Les actions ne sont volontairement pas transmises : la console n'a pas
        besoin de savoir quelle commande sera lancée, et cela évite d'exposer
        des chemins ou des URL sur le réseau.

        Le libellé est résolu ici, dans la langue annoncée par la console : la
        console reçoit donc un texte prêt à afficher et n'a pas à connaître les
        variantes.
        """
        payload: dict[str, Any] = {
            "id": self.id,
            "slot": self.slot,
            "label": self.label(locale),
            "icon": self.icon,
            "color": self.color,
        }
        if self.toggle:
            payload["toggle"] = self.toggle
        if self.hold_labels:
            payload["hold_label"] = self.hold_label(locale)
        return payload


@dataclass
class ListEntry:
    """Élément d'une page en mode liste.

    Contrairement à un bouton, un élément porte deux lignes de texte : le
    libellé principal et un détail. C'est ce qui permet de distinguer deux
    fenêtres d'une même application.
    """

    id: str
    label: str
    detail: str = ""
    icon: str = "app"
    color: str = "#64748B"
    active: bool = False
    action: Action = field(default_factory=lambda: Action("noop"))

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "icon": self.icon,
            "color": self.color,
        }
        if self.detail:
            payload["detail"] = self.detail
        if self.active:
            payload["active"] = True
        return payload


@dataclass
class PageConfig:
    id: str
    #: Titre par langue.
    titles: dict[str, str] = field(default_factory=dict)
    #: Icône de l'onglet. Bien plus lisible qu'un numéro sur une barre étroite.
    icon: str = "page"
    dashboard: str = "auto"
    buttons: list[ButtonConfig] = field(default_factory=list)
    #: Source alimentant automatiquement les boutons de la page.
    #: `windows` remplit la page avec les fenêtres ouvertes.
    source: str = ""
    #: Présentation : `grid` pour la grille de boutons, `list` pour une liste
    #: défilante adaptée à un contenu de longueur variable.
    layout: str = "grid"
    #: Éléments affichés lorsque `layout` vaut `list`.
    entries: list[ListEntry] = field(default_factory=list)

    def title(self, locale: str = "en") -> str:
        return self.titles.get(locale) or self.titles.get("en", self.id)

    def as_payload(self, locale: str = "en") -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "title": self.title(locale),
            "icon": self.icon,
            "dashboard": self.dashboard,
            "layout": self.layout,
        }

        if self.layout == "list":
            payload["entries"] = [entry.as_payload() for entry in self.entries]
            # La console attend toujours le tableau des boutons, même vide.
            payload["buttons"] = []
        else:
            payload["buttons"] = [button.as_payload(locale) for button in self.buttons]

        return payload

    def find_entry(self, entry_id: str) -> ListEntry | None:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None


@dataclass
class ObsConfig:
    """Connexion optionnelle au serveur WebSocket d'OBS Studio."""

    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 4455
    password: str = ""
    timeout: float = 2.0


@dataclass
class FeaturesConfig:
    """Services que l'utilisateur autorise l'agent à collecter."""

    notifications: bool = True
    media: bool = True
    media_artwork: bool = True
    windows: bool = True
    audio_output: bool = True
    system_stats: bool = True
    apple_music: bool = True
    spotify: bool = True


@dataclass
class Config:
    revision: int = 1
    host: str = "0.0.0.0"
    port: int = 38123
    token: str = ""
    poll_interval: float = 1.0
    volume_step: int = 5
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    obs: ObsConfig = field(default_factory=ObsConfig)
    pages: list[PageConfig] = field(default_factory=list)
    scripts: dict[str, list[str]] = field(default_factory=dict)

    def snapshot_payload(self, locale: str = "en") -> dict[str, Any]:
        return {
            "type": "config.snapshot",
            "revision": self.revision,
            "pages": [page.as_payload(locale) for page in self.pages],
        }

    def find_button(self, page_id: str, button_id: str) -> ButtonConfig | None:
        for page in self.pages:
            if page.id != page_id:
                continue
            for button in page.buttons:
                if button.id == button_id:
                    return button
        return None

    def find_action(self, page_id: str, item_id: str) -> Action | None:
        """Action associée à un bouton ou à un élément de liste.

        Les deux présentations partagent le même message d'appui : la résolution
        est donc centralisée ici plutôt que dupliquée dans le serveur.
        """
        for page in self.pages:
            if page.id != page_id:
                continue

            for button in page.buttons:
                if button.id == item_id:
                    return button.action

            entry = page.find_entry(item_id)
            if entry is not None:
                return entry.action

        return None


#: Langues acceptées pour les textes localisables des boutons et des pages.
LOCALES = ("en", "fr")

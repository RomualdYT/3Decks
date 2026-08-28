"""Chargement et validation de la configuration.

La configuration décrit les pages, les boutons et l'action associée à chacun.
Elle est validée en profondeur : la 3DS ne doit jamais recevoir une structure
incohérente, et un fichier mal écrit doit produire un message clair plutôt
qu'une interface vide.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .action_catalog import ACTION_SPECS
from .feature_catalog import FEATURE_SPECS
from .keys import InvalidHotkey, parse_hotkey

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
    kind: spec.arguments[0].name
    for kind, spec in ACTION_SPECS.items()
    if spec.arguments
}
ACTION_CAPABILITY = {
    kind: spec.capability
    for kind, spec in ACTION_SPECS.items()
    if spec.capability is not None
}


def action_arguments(kind: str) -> list[dict[str, Any]]:
    """Champs configurables d'une action, issus du catalogue partagé."""
    spec = ACTION_SPECS.get(kind)
    return [] if spec is None else [argument.as_payload() for argument in spec.arguments]

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

#: Icônes connues de l'application 3DS.
ICONS = {
    "mic",
    "mic-off",
    "volume-up",
    "volume-down",
    "volume-mute",
    "play",
    "pause",
    "next",
    "previous",
    "app",
    "browser",
    "terminal",
    "folder",
    "music",
    "chat",
    "video",
    "record",
    "lock",
    "page",
    "power",
    "gear",
    "star",
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
            payload["buttons"] = [
                button.as_payload(locale) for button in self.buttons
            ]

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
        raise ConfigError(
            f"{context}: une chaine ou un objet par langue est attendu"
        )

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


def _split_action(raw: Any, context: str) -> tuple[str, dict[str, Any]]:
    """Sépare le type de l'action de ses arguments.

    Deux écritures sont acceptées : la forme abrégée `"media.play_pause"`,
    lorsque l'action n'a pas d'argument, et la forme complète `{"type": ...}`.
    """
    if isinstance(raw, str):
        return raw.strip(), {}
    if isinstance(raw, dict):
        kind = raw.get("type")
        if not isinstance(kind, str):
            raise ConfigError(f"{context}: champ 'type' manquant")
        return kind.strip(), {
            key: value for key, value in raw.items() if key != "type"
        }
    raise ConfigError(f"{context}: action invalide")


def _check_action_args(kind: str, args: dict[str, Any], context: str) -> None:
    """Valide les arguments d'une action et normalise ce qui peut l'être.

    Le contrôle a lieu au chargement plutôt qu'à l'usage : une erreur de frappe
    est ainsi signalée dans l'éditeur, et non à l'appui du bouton sur la console.
    `args` est modifié sur place lorsqu'une valeur admet une forme canonique.
    """
    for argument in action_arguments(kind):
        name = argument["name"]
        if argument.get("required") and name not in args:
            raise ConfigError(f"{context}: l'action '{kind}' exige '{name}'")

        # Un raccourci mal écrit — `ctrl+alt+banane` — était accepté ici pour
        # n'échouer que sur la console. La forme retenue est normalisée, afin
        # que `shift+cmd+a` et `cmd+shift+a` ne donnent pas deux écritures.
        if argument.get("type") == "hotkey" and name in args:
            try:
                args[name] = parse_hotkey(args[name]).canonical()
            except InvalidHotkey as error:
                raise ConfigError(f"{context}.{name}: {error}") from error


def _parse_action(raw: Any, context: str) -> Action:
    if raw is None:
        return Action("noop")

    kind, args = _split_action(raw, context)
    if kind not in KNOWN_ACTIONS:
        known = ", ".join(sorted(KNOWN_ACTIONS))
        raise ConfigError(f"{context}: action inconnue '{kind}'. Connues: {known}")

    _check_action_args(kind, args, context)
    return Action(kind, args)


def _parse_button(raw: Any, index: int, context: str) -> ButtonConfig:
    if not isinstance(raw, dict):
        raise ConfigError(f"{context}: un objet est attendu")

    button_id = _require_str(raw.get("id"), f"{context}.id", MAX_ID)
    labels = _localised(raw.get("label", button_id), f"{context}.label", MAX_LABEL)

    slot = _require_slot(raw.get("slot", index), f"{context}.slot")
    icon = _require_choice(
        raw.get("icon", "app"),
        f"{context}.icon",
        ICONS,
        f"Connues: {', '.join(sorted(ICONS))}",
    )

    color = raw.get("color", DEFAULT_BUTTON_COLOR)
    if not isinstance(color, str) or not _is_hex_color(color):
        raise ConfigError(f"{context}.color: '{color}' n'est pas un code #RRGGBB")

    toggle = raw.get("toggle", "")
    if not isinstance(toggle, str):
        raise ConfigError(f"{context}.toggle: une chaine est attendue")

    raw_hold = raw.get("hold_label", "")
    hold_labels: dict[str, str] = {}
    if raw_hold:
        hold_labels = _localised(raw_hold, f"{context}.hold_label", MAX_LABEL)

    action = _parse_action(raw.get("action"), f"{context}.action")

    hold_action = None
    if raw.get("hold_action") is not None:
        hold_action = _parse_action(raw.get("hold_action"), f"{context}.hold_action")

    return ButtonConfig(
        id=button_id,
        slot=slot,
        labels=labels,
        icon=icon,
        color=color.upper(),
        toggle=toggle,
        hold_labels=hold_labels,
        action=action,
        hold_action=hold_action,
    )


def _is_hex_color(value: str) -> bool:
    if not value.startswith("#"):
        return False
    digits = value[1:]
    if len(digits) not in (3, 6):
        return False
    return all(character in "0123456789abcdefABCDEF" for character in digits)


def _parse_buttons(raw: Any, context: str) -> list[ButtonConfig]:
    """Boutons d'une page, emplacements et identifiants vérifiés uniques.

    Deux boutons partageant un emplacement en masqueraient un ; deux
    identifiants identiques rendraient l'un des deux inatteignable.
    """
    if not isinstance(raw, list):
        raise ConfigError(f"{context}.buttons: une liste est attendue")
    if len(raw) > MAX_BUTTONS_PER_PAGE:
        raise ConfigError(
            f"{context}.buttons: {len(raw)} boutons, "
            f"maximum {MAX_BUTTONS_PER_PAGE}"
        )

    buttons = [
        _parse_button(item, position, f"{context}.buttons[{position}]")
        for position, item in enumerate(raw)
    ]

    duplicates = _duplicates([button.slot for button in buttons])
    if duplicates:
        raise ConfigError(f"{context}: emplacements en double: {duplicates}")

    duplicate_ids = _duplicates([button.id for button in buttons])
    if duplicate_ids:
        raise ConfigError(f"{context}: identifiants en double: {duplicate_ids}")

    return buttons


def _parse_page(raw: Any, index: int) -> PageConfig:
    context = f"pages[{index}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{context}: un objet est attendu")

    page_id = _require_str(raw.get("id"), f"{context}.id", MAX_ID)
    titles = _localised(raw.get("title", page_id), f"{context}.title", MAX_LABEL)

    dashboard = _require_choice(
        raw.get("dashboard", "auto"),
        f"{context}.dashboard",
        DASHBOARDS,
        f"Connus: {', '.join(sorted(DASHBOARDS))}",
        feminine=False,
    )
    page_icon = _require_choice(
        raw.get("icon", "page"),
        f"{context}.icon",
        ICONS,
        f"Connues: {', '.join(sorted(ICONS))}",
    )
    layout = _require_choice(
        raw.get("layout", "grid"), f"{context}.layout", ("grid", "list"),
        "Connues: grid, list",
    )
    source = _require_choice(
        raw.get("source", ""), f"{context}.source", ("", "windows"),
        "Connue: windows",
    )

    buttons = _parse_buttons(raw.get("buttons", []), context)

    return PageConfig(
        id=page_id,
        titles=titles,
        icon=page_icon,
        dashboard=dashboard,
        buttons=buttons,
        source=source,
        layout=layout,
    )


def parse_obs(raw: Any) -> ObsConfig:
    """Valide la section OBS, reutilisee par le fichier et le test de l'UI."""
    if raw is None:
        return ObsConfig()
    if not isinstance(raw, dict):
        raise ConfigError("integrations.obs: un objet est attendu")

    defaults = ObsConfig()
    enabled = raw.get("enabled", defaults.enabled)
    if not isinstance(enabled, bool):
        raise ConfigError("integrations.obs.enabled: un booleen est attendu")

    host = _require_host(raw.get("host", defaults.host), "integrations.obs.host")
    port = _require_port(raw.get("port", defaults.port), "integrations.obs.port")

    password = raw.get("password", defaults.password)
    if not isinstance(password, str):
        raise ConfigError("integrations.obs.password: une chaine est attendue")

    timeout = _require_seconds(
        raw.get("timeout", defaults.timeout),
        "integrations.obs.timeout",
        *OBS_TIMEOUT_RANGE,
    )

    return ObsConfig(
        enabled=enabled,
        host=host,
        port=port,
        password=password,
        timeout=timeout,
    )


def _apply_server(raw: Any, config: Config) -> None:
    """Applique la section `server`, en conservant les défauts absents."""
    if raw is None:
        return
    if not isinstance(raw, dict):
        raise ConfigError("server: un objet est attendu")
    if not raw:
        return

    config.host = _require_host(raw.get("host", config.host), "server.host")
    config.port = _require_port(raw.get("port", config.port), "server.port")

    token = raw.get("token", "")
    if not isinstance(token, str):
        raise ConfigError("server.token: une chaine est attendue")
    config.token = token.strip()

    config.poll_interval = _require_seconds(
        raw.get("poll_interval", config.poll_interval),
        "server.poll_interval",
        *POLL_INTERVAL_RANGE,
    )
    config.volume_step = _require_step(
        raw.get("volume_step", config.volume_step), "server.volume_step"
    )


def _parse_scripts(raw: Any) -> dict[str, list[str]]:
    """Commandes autorisées, référencées par leur nom depuis les boutons."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError("scripts: un objet est attendu")
    if not raw:
        return {}

    scripts: dict[str, list[str]] = {}
    for name, command in raw.items():
        if not isinstance(command, list) or not command:
            raise ConfigError(
                f"scripts.{name}: une liste d'arguments non vide est attendue"
            )
        if not all(isinstance(item, str) for item in command):
            raise ConfigError(f"scripts.{name}: arguments textuels attendus")
        scripts[str(name)] = list(command)
    return scripts


def _parse_integrations(raw: Any, config: Config) -> None:
    if raw is None:
        return
    if not isinstance(raw, dict):
        raise ConfigError("integrations: un objet est attendu")
    if not raw:
        return
    if "obs" in raw:
        config.obs = parse_obs(raw["obs"])


def _parse_features(raw: Any) -> FeaturesConfig:
    """Valide les collectes optionnelles et leurs dépendances."""
    if raw is None:
        return FeaturesConfig()
    if not isinstance(raw, dict):
        raise ConfigError("features: un objet est attendu")

    unknown = set(raw) - set(FEATURE_SPECS)
    if unknown:
        raise ConfigError(f"features: options inconnues {sorted(unknown)}")

    defaults = FeaturesConfig()
    values: dict[str, bool] = {}
    for name in FEATURE_SPECS:
        value = raw.get(name, getattr(defaults, name))
        if not isinstance(value, bool):
            raise ConfigError(f"features.{name}: un booleen est attendu")
        values[name] = value

    # Une sous-fonction désactivée avec son parent est normalisée plutôt que
    # rejetée : l'interface peut conserver le choix pour le prochain réemploi.
    return FeaturesConfig(**values)


def _parse_pages(raw: Any) -> list[PageConfig]:
    if not isinstance(raw, list) or not raw:
        raise ConfigError("pages: une liste non vide est attendue")
    if len(raw) > MAX_PAGES:
        raise ConfigError(f"pages: {len(raw)} pages, maximum {MAX_PAGES}")

    pages = [_parse_page(item, index) for index, item in enumerate(raw)]

    duplicates = _duplicates([page.id for page in pages])
    if duplicates:
        raise ConfigError(f"pages: identifiants en double: {duplicates}")
    return pages


def _each_action(pages: list[PageConfig]):
    """Parcourt toutes les actions déclarées, appui long compris."""
    return (
        (page, button, action)
        for page in pages
        for button in page.buttons
        for action in (button.action, button.hold_action)
        if action is not None
    )


def _check_references(
    pages: list[PageConfig], kind: str, argument: str, known, complaint: str
) -> None:
    """Vérifie que les actions d'un type donné visent une cible existante.

    Une référence brisée ne se verrait qu'à l'appui du bouton, sur la console :
    la signaler au chargement évite ce détour. La navigation et les scripts
    partagent ce contrôle, seul le vocabulaire du message diffère.
    """
    for page, button, action in _each_action(pages):
        if action.kind != kind:
            continue
        target = action.args.get(argument)
        if target not in known:
            raise ConfigError(
                f"pages[{page.id}].{button.id}: {complaint.format(target=target)}"
            )


def parse(raw: Any) -> Config:
    """Valide une structure déjà décodée et retourne la configuration.

    Chaque section est validée par une fonction dédiée ; ne subsiste ici que
    l'enchaînement, et les vérifications qui exigent la configuration complète.
    """
    if not isinstance(raw, dict):
        raise ConfigError("la racine doit etre un objet")

    config = Config()
    _apply_server(raw.get("server", {}), config)
    config.revision = _require_int(raw.get("revision", 1), "revision")
    config.features = _parse_features(raw.get("features", {}))
    _parse_integrations(raw.get("integrations", {}), config)
    config.scripts = _parse_scripts(raw.get("scripts", {}))
    config.pages = _parse_pages(raw.get("pages", []))

    # Vérifications croisées : elles supposent toutes les pages et tous les
    # scripts déjà connus, et ne peuvent donc pas être faites plus tôt.
    _check_references(
        config.pages,
        "page.open",
        "page",
        {page.id for page in config.pages},
        "page cible '{target}' inexistante",
    )
    _check_references(
        config.pages,
        "script.run",
        "script",
        config.scripts,
        "script '{target}' non declare dans 'scripts'",
    )
    return config


def _localised_to_raw(texts: dict[str, str]) -> Any:
    """Réécrit un texte localisé sous sa forme la plus concise.

    Une valeur identique dans toutes les langues redevient une simple chaîne :
    le fichier reste lisible et ne s'alourdit pas de traductions inutiles.
    """
    if not texts:
        return ""

    values = {texts.get(locale, "") for locale in LOCALES}
    if len(values) == 1:
        return texts.get("en", "")

    return {locale: texts.get(locale, "") for locale in LOCALES}


def _action_to_raw(action: Action | None) -> Any:
    """Réécrit une action sous sa forme la plus concise."""
    if action is None:
        return None
    if not action.args:
        return action.kind
    return {"type": action.kind, **action.args}


def _button_to_raw(button: ButtonConfig) -> dict[str, Any]:
    """Écriture concise d'un bouton : les valeurs par défaut sont omises."""
    raw: dict[str, Any] = {
        "id": button.id,
        "slot": button.slot,
        "label": _localised_to_raw(button.labels),
        "icon": button.icon,
        "color": button.color,
    }
    if button.toggle:
        raw["toggle"] = button.toggle
    if button.hold_labels:
        raw["hold_label"] = _localised_to_raw(button.hold_labels)

    raw["action"] = _action_to_raw(button.action)
    if button.hold_action is not None:
        raw["hold_action"] = _action_to_raw(button.hold_action)
    return raw


def _page_to_raw(page: PageConfig) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "id": page.id,
        "title": _localised_to_raw(page.titles),
        "icon": page.icon,
        "dashboard": page.dashboard,
    }
    if page.layout != "grid":
        raw["layout"] = page.layout
    if page.source:
        raw["source"] = page.source

    # Le contenu d'une page dynamique appartient à l'état d'exécution, pas au
    # fichier. Sans cette frontière, ouvrir l'éditeur puis enregistrer un autre
    # réglage inscrirait les fenêtres du moment dans `config.json`.
    if page.source:
        raw["buttons"] = []
    else:
        # Les boutons sont rangés par emplacement : le fichier reflète alors
        # l'ordre visible sur la console.
        raw["buttons"] = [
            _button_to_raw(button)
            for button in sorted(page.buttons, key=lambda item: item.slot)
        ]
    return raw


def to_raw(config: Config) -> dict[str, Any]:
    """Reconstruit la structure du fichier depuis une configuration chargée.

    Cette fonction est l'inverse de `parse` : elle permet à l'interface de
    relire, modifier puis réenregistrer la configuration sans en perdre le
    contenu ni la mise en forme concise.
    """
    raw: dict[str, Any] = {
        "revision": config.revision,
        "server": {
            "host": config.host,
            "port": config.port,
            "token": config.token,
            "poll_interval": config.poll_interval,
            "volume_step": config.volume_step,
        },
        "features": {
            name: getattr(config.features, name) for name in FEATURE_SPECS
        },
        "integrations": {
            "obs": {
                "enabled": config.obs.enabled,
                "host": config.obs.host,
                "port": config.obs.port,
                "password": config.obs.password,
                "timeout": config.obs.timeout,
            }
        },
    }

    if config.scripts:
        raw["scripts"] = {
            name: list(command) for name, command in config.scripts.items()
        }

    raw["pages"] = [_page_to_raw(page) for page in config.pages]
    return raw


def save(config: Config, path: Path) -> None:
    """Enregistre une configuration, en validant avant d'écrire.

    L'écriture passe par un fichier temporaire renommé ensuite : une
    interruption ne peut donc pas laisser une configuration tronquée, ce qui
    priverait la console de toute interface.
    """
    raw = to_raw(config)

    # Vérification de cohérence : mieux vaut refuser d'écrire qu'enregistrer
    # une configuration que l'agent ne saurait plus relire.
    parse(raw)

    text = json.dumps(raw, ensure_ascii=False, indent=2) + "\n"

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def load(path: Path) -> Config:
    """Charge la configuration depuis un fichier JSON."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ConfigError(f"fichier introuvable: {path}") from error
    except OSError as error:
        raise ConfigError(f"lecture impossible: {error}") from error

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"JSON invalide ligne {error.lineno}, colonne {error.colno}: {error.msg}"
        ) from error

    return parse(raw)

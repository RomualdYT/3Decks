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

#: Actions acceptées. Toute autre valeur est rejetée au chargement : la 3DS ne
#: peut donc pas déclencher d'exécution arbitraire, même si elle était
#: compromise.
KNOWN_ACTIONS = {
    "volume.up",
    "volume.down",
    "volume.set",
    "volume.mute_toggle",
    # Volume interne du lecteur, utile quand le son sort sur une enceinte
    # externe et que le volume système n'agit plus sur la musique.
    "app_volume.up",
    "app_volume.down",
    "app_volume.set",
    # Bascule de la sortie audio : casque, enceinte, écran...
    "audio_output.cycle",
    "audio_output.set",
    "mic.mute_toggle",
    "mic.mute",
    "mic.unmute",
    "media.play_pause",
    "media.next",
    "media.previous",
    "app.launch",
    "app.quit",
    # Sélection d'une fenêtre ouverte, alimentée dynamiquement par l'agent.
    "window.focus",
    "url.open",
    "path.open",
    "hotkey",
    "script.run",
    "page.open",
    # Ouvre l'écran de réglages de la console, sans action côté ordinateur.
    "settings.open",
    # Ouvre le panneau de volumes de la console.
    "modal.volumes",
    # Bascule l'affichage plein écran, réutilisé par la veille.
    "frame.toggle",
    "system.lock",
    # OBS Studio, via le serveur WebSocket integre a OBS 28 et suivants.
    "obs.scene.set",
    "obs.stream.toggle",
    "obs.record.toggle",
    "obs.source.toggle",
    "noop",
}

#: Argument obligatoire de chaque action qui en exige un.
#:
#: Défini ici plutôt que dans le validateur : l'interface a besoin de la même
#: table pour demander le bon champ, et une seconde copie finirait par diverger.
ACTION_REQUIRED_ARG = {
    "app.launch": "target",
    "app.quit": "target",
    "url.open": "url",
    "path.open": "path",
    "hotkey": "keys",
    "script.run": "script",
    "page.open": "page",
    "volume.set": "value",
    "app_volume.set": "value",
    "audio_output.set": "target",
    "obs.scene.set": "scene",
    # `obs.source.toggle` exige egalement `source`; voir `action_arguments`.
    "obs.source.toggle": "scene",
}


def action_arguments(kind: str) -> list[dict[str, Any]]:
    """Champs configurables d'une action, exposes tels quels a l'interface.

    La plupart des actions historiques n'ont qu'un argument obligatoire. OBS a
    besoin de deux valeurs pour une source (scene + source), d'ou ce contrat un
    peu plus riche. Le conserver pres du validateur evite que l'editeur et
    l'agent divergent lorsqu'une nouvelle action est ajoutee.
    """
    if kind == "obs.source.toggle":
        return [
            {"name": "scene", "type": "text", "required": True},
            {"name": "source", "type": "text", "required": True},
        ]

    required = ACTION_REQUIRED_ARG.get(kind)
    if required is None:
        return []

    field_type = {
        "page": "page",
        "script": "script",
        "value": "number",
    }.get(required, "text")
    return [{"name": required, "type": field_type, "required": True}]

#: Capacité de plateforme exigée par chaque action.
#:
#: Une action absente de cette table fonctionne partout : elle est traitée par
#: la console elle-même (`settings.open`, `page.open`...) ou ne fait rien.
#: Sert à l'interface pour signaler un bouton qui resterait sans effet sur le
#: poste courant, plutôt que de le laisser paraître fonctionnel.
ACTION_CAPABILITY = {
    "volume.up": "volume",
    "volume.down": "volume",
    "volume.set": "volume",
    "volume.mute_toggle": "mute",
    "app_volume.up": "app_volume",
    "app_volume.down": "app_volume",
    "app_volume.set": "app_volume",
    "audio_output.cycle": "audio_output",
    "audio_output.set": "audio_output",
    "mic.mute_toggle": "mic",
    "mic.mute": "mic",
    "mic.unmute": "mic",
    "media.play_pause": "media",
    "media.next": "media",
    "media.previous": "media",
    "app.launch": "apps",
    "app.quit": "apps",
    "window.focus": "windows",
    "url.open": "open_url",
    "path.open": "open_path",
    "hotkey": "hotkey",
    "system.lock": "lock",
    "obs.scene.set": "obs",
    "obs.stream.toggle": "obs",
    "obs.record.toggle": "obs",
    "obs.source.toggle": "obs",
}

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
    color: str = "#3B82F6"
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
class Config:
    revision: int = 1
    host: str = "0.0.0.0"
    port: int = 38123
    token: str = ""
    poll_interval: float = 1.0
    volume_step: int = 5
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
    if not 1 <= port <= 65535:
        raise ConfigError(f"{context}: {port} hors bornes")
    return port


def _require_host(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context}: adresse invalide")
    return value.strip()


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


def _parse_action(raw: Any, context: str) -> Action:
    if raw is None:
        return Action("noop")

    if isinstance(raw, str):
        # Forme abrégée : "media.play_pause"
        kind = raw.strip()
        args: dict[str, Any] = {}
    elif isinstance(raw, dict):
        kind_value = raw.get("type")
        if not isinstance(kind_value, str):
            raise ConfigError(f"{context}: champ 'type' manquant")
        kind = kind_value.strip()
        args = {key: value for key, value in raw.items() if key != "type"}
    else:
        raise ConfigError(f"{context}: action invalide")

    if kind not in KNOWN_ACTIONS:
        known = ", ".join(sorted(KNOWN_ACTIONS))
        raise ConfigError(f"{context}: action inconnue '{kind}'. Connues: {known}")

    # Validation des arguments obligatoires, au chargement plutôt qu'à l'usage :
    # une erreur de frappe est ainsi signalée immédiatement.
    for argument in action_arguments(kind):
        name = argument["name"]
        if argument.get("required") and name not in args:
            raise ConfigError(f"{context}: l'action '{kind}' exige '{name}'")

    return Action(kind, args)


def _parse_button(raw: Any, index: int, context: str) -> ButtonConfig:
    if not isinstance(raw, dict):
        raise ConfigError(f"{context}: un objet est attendu")

    button_id = _require_str(raw.get("id"), f"{context}.id", MAX_ID)
    labels = _localised(raw.get("label", button_id), f"{context}.label", MAX_LABEL)

    slot = raw.get("slot", index)
    if not isinstance(slot, int) or isinstance(slot, bool):
        raise ConfigError(f"{context}.slot: un entier est attendu")
    if not 0 <= slot < MAX_BUTTONS_PER_PAGE:
        raise ConfigError(
            f"{context}.slot: {slot} hors bornes (0 a {MAX_BUTTONS_PER_PAGE - 1})"
        )

    icon = raw.get("icon", "app")
    if not isinstance(icon, str) or icon not in ICONS:
        raise ConfigError(
            f"{context}.icon: '{icon}' inconnue. Connues: {', '.join(sorted(ICONS))}"
        )

    color = raw.get("color", "#3B82F6")
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


def _parse_page(raw: Any, index: int) -> PageConfig:
    context = f"pages[{index}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{context}: un objet est attendu")

    page_id = _require_str(raw.get("id"), f"{context}.id", MAX_ID)
    titles = _localised(raw.get("title", page_id), f"{context}.title", MAX_LABEL)

    dashboard = raw.get("dashboard", "auto")
    if not isinstance(dashboard, str) or dashboard not in DASHBOARDS:
        raise ConfigError(
            f"{context}.dashboard: '{dashboard}' inconnu. "
            f"Connus: {', '.join(sorted(DASHBOARDS))}"
        )

    page_icon = raw.get("icon", "page")
    if not isinstance(page_icon, str) or page_icon not in ICONS:
        raise ConfigError(
            f"{context}.icon: '{page_icon}' inconnue. "
            f"Connues: {', '.join(sorted(ICONS))}"
        )

    layout = raw.get("layout", "grid")
    if not isinstance(layout, str) or layout not in ("grid", "list"):
        raise ConfigError(
            f"{context}.layout: '{layout}' inconnue. Connues: grid, list"
        )

    source = raw.get("source", "")
    if not isinstance(source, str) or source not in ("", "windows"):
        raise ConfigError(
            f"{context}.source: '{source}' inconnue. Connue: windows"
        )

    raw_buttons = raw.get("buttons", [])
    if not isinstance(raw_buttons, list):
        raise ConfigError(f"{context}.buttons: une liste est attendue")
    if len(raw_buttons) > MAX_BUTTONS_PER_PAGE:
        raise ConfigError(
            f"{context}.buttons: {len(raw_buttons)} boutons, "
            f"maximum {MAX_BUTTONS_PER_PAGE}"
        )

    buttons = [
        _parse_button(item, position, f"{context}.buttons[{position}]")
        for position, item in enumerate(raw_buttons)
    ]

    duplicates = _duplicates([button.slot for button in buttons])
    if duplicates:
        raise ConfigError(f"{context}: emplacements en double: {duplicates}")

    duplicate_ids = _duplicates([button.id for button in buttons])
    if duplicate_ids:
        raise ConfigError(f"{context}: identifiants en double: {duplicate_ids}")

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
        raw.get("timeout", defaults.timeout), "integrations.obs.timeout", 0.2, 15.0
    )

    return ObsConfig(
        enabled=enabled,
        host=host,
        port=port,
        password=password,
        timeout=timeout,
    )


def parse(raw: Any) -> Config:
    """Valide une structure déjà décodée et retourne la configuration."""
    if not isinstance(raw, dict):
        raise ConfigError("la racine doit etre un objet")

    config = Config()

    server = raw.get("server", {})
    if server:
        if not isinstance(server, dict):
            raise ConfigError("server: un objet est attendu")

        config.host = _require_host(server.get("host", config.host), "server.host")
        config.port = _require_port(server.get("port", config.port), "server.port")

        token = server.get("token", "")
        if not isinstance(token, str):
            raise ConfigError("server.token: une chaine est attendue")
        config.token = token.strip()

        config.poll_interval = _require_seconds(
            server.get("poll_interval", config.poll_interval),
            "server.poll_interval",
            0.2,
            30.0,
        )

        step = server.get("volume_step", config.volume_step)
        if not isinstance(step, int) or isinstance(step, bool) or not 1 <= step <= 50:
            raise ConfigError("server.volume_step: entier entre 1 et 50")
        config.volume_step = step

    config.revision = _require_int(raw.get("revision", 1), "revision")

    integrations = raw.get("integrations", {})
    if integrations:
        if not isinstance(integrations, dict):
            raise ConfigError("integrations: un objet est attendu")

        if "obs" in integrations:
            config.obs = parse_obs(integrations["obs"])

    scripts = raw.get("scripts", {})
    if scripts:
        if not isinstance(scripts, dict):
            raise ConfigError("scripts: un objet est attendu")
        for name, command in scripts.items():
            if not isinstance(command, list) or not command:
                raise ConfigError(
                    f"scripts.{name}: une liste d'arguments non vide est attendue"
                )
            if not all(isinstance(item, str) for item in command):
                raise ConfigError(f"scripts.{name}: arguments textuels attendus")
            config.scripts[str(name)] = list(command)

    raw_pages = raw.get("pages", [])
    if not isinstance(raw_pages, list) or not raw_pages:
        raise ConfigError("pages: une liste non vide est attendue")
    if len(raw_pages) > MAX_PAGES:
        raise ConfigError(f"pages: {len(raw_pages)} pages, maximum {MAX_PAGES}")

    config.pages = [_parse_page(item, index) for index, item in enumerate(raw_pages)]

    page_ids = [page.id for page in config.pages]
    duplicates = _duplicates(page_ids)
    if duplicates:
        raise ConfigError(f"pages: identifiants en double: {duplicates}")

    # Vérification croisée : une navigation ne doit pas pointer dans le vide.
    for page in config.pages:
        for button in page.buttons:
            for action in (button.action, button.hold_action):
                if action is None or action.kind != "page.open":
                    continue
                target = action.args.get("page")
                if target not in page_ids:
                    raise ConfigError(
                        f"pages[{page.id}].{button.id}: page cible "
                        f"'{target}' inexistante"
                    )

    # Vérification croisée des scripts référencés.
    for page in config.pages:
        for button in page.buttons:
            for action in (button.action, button.hold_action):
                if action is None or action.kind != "script.run":
                    continue
                name = action.args.get("script")
                if name not in config.scripts:
                    raise ConfigError(
                        f"pages[{page.id}].{button.id}: script "
                        f"'{name}' non declare dans 'scripts'"
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

    pages: list[dict[str, Any]] = []

    for page in config.pages:
        entry: dict[str, Any] = {
            "id": page.id,
            "title": _localised_to_raw(page.titles),
            "icon": page.icon,
            "dashboard": page.dashboard,
        }

        if page.layout != "grid":
            entry["layout"] = page.layout
        if page.source:
            entry["source"] = page.source

        buttons: list[dict[str, Any]] = []

        for button in sorted(page.buttons, key=lambda item: item.slot):
            raw_button: dict[str, Any] = {
                "id": button.id,
                "slot": button.slot,
                "label": _localised_to_raw(button.labels),
                "icon": button.icon,
                "color": button.color,
            }

            if button.toggle:
                raw_button["toggle"] = button.toggle
            if button.hold_labels:
                raw_button["hold_label"] = _localised_to_raw(button.hold_labels)

            raw_button["action"] = _action_to_raw(button.action)

            if button.hold_action is not None:
                raw_button["hold_action"] = _action_to_raw(button.hold_action)

            buttons.append(raw_button)

        entry["buttons"] = buttons
        pages.append(entry)

    raw["pages"] = pages
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

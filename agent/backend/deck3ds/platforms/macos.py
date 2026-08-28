"""Adaptateur macOS.

Points vérifiés sur macOS 27 avant écriture de ce module :

- `output volume` et `output muted` sont fiables via AppleScript ;
- `input volume` renvoie souvent `missing value` : l'état du micro n'est donc
  pas observable de façon fiable. On suit l'état localement et on l'annonce
  comme inconnu tant que l'utilisateur n'a rien changé ;
- une requête AppleScript vers une application tierce peut se bloquer
  indéfiniment en attendant l'autorisation d'automatisation du système. Tous les
  appels sont donc bornés par un délai court.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import re
from pathlib import Path

from ..config import MAX_LIST_ENTRIES
from ..coreaudio import CoreAudio
from ..keys import InvalidHotkey, parse_hotkey
from ..messages import msg
from .macos_notifications import NotificationReader
from .macos_media import MEDIA_PLAYERS as MEDIA_PLAYERS
from .macos_media import MacMediaProvider, parse_number as _parse_number
from .macos_windows import WindowLister
from .base import (
    ActionFailed,
    Capabilities,
    MediaInfo,
    NotificationInfo,
    Platform,
    SelectionCancelled,
    SystemSnapshot,
    Unsupported,
)

#: Délai maximal d'un appel AppleScript. Volontairement court : une application
#: qui ne répond pas ne doit pas retarder le tableau de bord.
SCRIPT_TIMEOUT = 2.5

#: Processus présents dans la liste des applications sans en être : les afficher
#: sur la console n'aurait aucun intérêt. Le filtrage sert à deux endroits
#: (`list_apps` et la collecte groupée), qui doivent rester cohérents.
_HIDDEN_PROCESSES = frozenset(
    {"FolderActionsDispatcher", "Dock", "SystemUIServer", ""}
)

def _visible_apps(raw: str) -> list[str]:
    """Découpe une liste d'applications AppleScript en masquant les processus
    techniques.

    Deux chemins produisent cette liste — la collecte groupée et son repli
    `list_apps` — et doivent filtrer à l'identique.
    """
    return [
        name.strip()
        for name in raw.split(",")
        if name.strip() not in _HIDDEN_PROCESSES
    ]


class MacPlatform(Platform):
    name = "darwin"

    def __init__(self, features: object | None = None) -> None:
        if features is not None:
            self.configure_features(features)
        # Accès direct à CoreAudio pour les sorties audio : aucun utilitaire
        # externe n'est ainsi nécessaire.
        self._audio = CoreAudio()
        # Énumération rapide des fenêtres, via CoreGraphics.
        self._windows = WindowLister()
        # Lecture du centre de notifications.
        self._notifications = NotificationReader()
        self._pending_notification: NotificationInfo | None = None
        # État du micro suivi localement, faute de lecture fiable.
        self._mic_muted: bool | None = None
        self._mic_restore = 75
        self._media = MacMediaProvider(
            self._script, self._script_quiet, self.feature_enabled
        )
        self._cpu_count: int | None = None

    # --- Capacités ------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        """Adaptateur de référence : tout est implémenté.

        `mic` reste déclaré vrai même si la lecture de l'état échoue souvent :
        le basculement fonctionne, seul l'affichage initial est approximatif.
        Les capacités décrivent ce qui est implémenté, pas ce que les
        autorisations du poste accordent — cela relève de `--probe`.
        """
        return Capabilities(
            volume=True,
            mute=True,
            mic=True,
            app_volume=True,
            audio_output=True,
            media=True,
            media_artwork=True,
            apps=True,
            windows=True,
            hotkey=True,
            open_url=True,
            open_path=True,
            lock=True,
            notifications=self._notifications.available
            and not self._notifications.broken,
            system_stats=True,
        )

    def notification_status(self) -> dict[str, object]:
        """État du lecteur historique macOS, faute d'API publique équivalente."""
        enabled = self.feature_enabled("notifications")
        available = self._notifications.probe() if enabled else False
        return {
            "provider": "macos_notification_database",
            "enabled": enabled,
            "available": available,
            "access": (
                "Disabled"
                if not enabled
                else "Allowed" if available else "Unavailable"
            ),
            "error": (
                self._notifications.last_error or "Centre de notifications inaccessible"
                if enabled and not available
                else ""
            ),
            "settings_action": (
                "notifications"
                if enabled and not available
                else ""
            ),
        }

    def open_permission_settings(self, permission: str) -> None:
        """Ouvre directement la section Confidentialité utile de macOS."""
        panels = {
            # La base Notification Center est protégée par Full Disk Access.
            "notifications": (
                "x-apple.systempreferences:com.apple.preference.security?"
                "Privacy_AllFiles"
            ),
            # Prévu pour les lecteurs AppleScript (Spotify / Apple Music).
            "automation": (
                "x-apple.systempreferences:com.apple.preference.security?"
                "Privacy_Automation"
            ),
        }
        panel = panels.get(permission)
        if panel is None:
            raise Unsupported("autorisation macOS inconnue")
        self.spawn(["open", panel])

    # --- AppleScript ----------------------------------------------------------

    def _script(self, source: str, timeout: float = SCRIPT_TIMEOUT) -> str:
        return self.run(["osascript", "-e", source], timeout=timeout).strip()

    def _script_quiet(self, source: str) -> str | None:
        """Variante tolérante : retourne `None` au lieu de lever."""
        try:
            return self._script(source)
        except (Unsupported, ActionFailed):
            return None

    # --- Volume ---------------------------------------------------------------

    def get_volume(self) -> int | None:
        raw = self._script_quiet("output volume of (get volume settings)")
        if raw is None or not raw.isdigit():
            return None
        return max(0, min(100, int(raw)))

    def set_volume(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        self._script(f"set volume output volume {value}")

    def is_muted(self) -> bool | None:
        raw = self._script_quiet("output muted of (get volume settings)")
        if raw is None:
            return None
        return raw == "true"

    def set_muted(self, muted: bool) -> None:
        self._script(f"set volume {'with' if muted else 'without'} output muted")

    # --- Volume du lecteur ----------------------------------------------------

    def get_app_volume(self) -> int | None:
        return self._media.get_volume()

    def set_app_volume(self, value: int) -> None:
        self._media.set_volume(value)

    # --- Microphone -----------------------------------------------------------

    def is_mic_muted(self) -> bool | None:
        """État du micro.

        `input volume` étant fréquemment indisponible, on tente la lecture puis
        on se rabat sur l'état suivi localement. Retourner `None` est préférable
        à une valeur inventée : la 3DS affiche alors « MICRO ? ».
        """
        raw = self._script_quiet("input volume of (get volume settings)")
        if raw is not None and raw.isdigit():
            return int(raw) == 0
        return self._mic_muted

    def set_mic_muted(self, muted: bool) -> None:
        if muted:
            # Mémorise le niveau courant pour le restaurer ensuite.
            raw = self._script_quiet("input volume of (get volume settings)")
            if raw is not None and raw.isdigit() and int(raw) > 0:
                self._mic_restore = int(raw)
            self._script("set volume input volume 0")
        else:
            self._script(f"set volume input volume {self._mic_restore}")

        self._mic_muted = muted

    # --- Notifications --------------------------------------------------------

    def list_notifications(self) -> list[NotificationInfo]:
        return self._read_notifications()

    def take_new_notification(self) -> NotificationInfo | None:
        return self._take_pending_notification()

    # --- Sortie audio ---------------------------------------------------------

    def get_audio_output(self) -> str:
        current = self._audio.default_output()
        if current is None:
            return ""
        for device in self._audio.outputs():
            if device.identifier == current:
                return device.name
        return ""

    def list_audio_outputs(self) -> list[str]:
        return [device.name for device in self._audio.outputs()]

    def cycle_audio_output(self) -> str:
        name = self._audio.cycle_output()
        if name is None:
            raise ActionFailed(msg("single_output"))
        return name

    def select_audio_output(self, needle: str) -> str:
        name = self._audio.select_output(needle)
        if name is None:
            raise ActionFailed(msg("output_not_found", name=needle))
        return name

    # --- Média ----------------------------------------------------------------

    def get_media(self) -> MediaInfo | None:
        return self._media.get_media()

    def media_play_pause(self) -> None:
        self._media.play_pause()

    def media_next(self) -> None:
        self._media.next()

    def media_previous(self) -> None:
        self._media.previous()

    # --- Applications ---------------------------------------------------------

    def get_active_app(self) -> str:
        raw = self._script_quiet(
            'tell application "System Events" to get name of first '
            "application process whose frontmost is true"
        )
        return raw or ""

    def list_apps(self) -> list[str]:
        raw = self._script_quiet(
            'tell application "System Events" to get name of every '
            "application process whose background only is false"
        )
        if not raw:
            return []

        return _visible_apps(raw)

    def list_launchable_apps(self) -> list[str]:
        """Applications installées proposées par le sélecteur de l'éditeur."""
        roots = (
            Path("/Applications"),
            Path("/System/Applications"),
            Path("/System/Applications/Utilities"),
            Path.home() / "Applications",
        )
        names: set[str] = set(self.list_apps())
        for root in roots:
            try:
                names.update(path.stem for path in root.glob("*.app") if path.is_dir())
            except OSError:
                continue
        return sorted(names, key=str.casefold)

    def list_windows(self) -> list[tuple[str, str]]:
        # La borne est celle annoncée à l'interface par le schéma : en retenir
        # moins ici ferait mentir la limite affichée à l'utilisateur.
        return [
            (window.app, window.title)
            for window in self._windows.list(limit=MAX_LIST_ENTRIES)
        ]

    def focus_window(self, app: str, title: str) -> str:
        """Ramène une fenêtre au premier plan.

        `open -a` est utilisé pour activer l'application : c'est la seule
        méthode qui s'est révélée fiable à l'usage. `activate` et
        `set frontmost` renvoient un succès mais restent parfois sans effet,
        notamment lorsque l'application n'a pas de fenêtre visible.

        Le titre sert ensuite à lever la bonne fenêtre parmi celles de
        l'application, ce qui compte pour un Finder ou un navigateur qui en
        ouvre plusieurs.
        """
        if not app:
            raise ActionFailed("application manquante")

        self.run(["open", "-a", app], timeout=8.0)

        if title:
            # `AXRaise` échoue silencieusement sur certaines applications : son
            # échec ne doit pas faire échouer l'action, l'essentiel étant que
            # l'application soit au premier plan.
            safe = title.replace("\\", "\\\\").replace('"', '\\"')
            self._script_quiet(
                'tell application "System Events"\n'
                f'  set deckProc to first application process whose name is "{app}"\n'
                "  try\n"
                "    perform action \"AXRaise\" of (first window of deckProc "
                f'whose name is "{safe}")\n'
                "  end try\n"
                "end tell"
            )

        return title if title else app

    def launch_app(self, target: str) -> None:
        # `open -a` accepte un nom d'application, un identifiant de paquet ou un
        # chemin, et ramène l'application au premier plan si elle tourne déjà.
        self.run(["open", "-a", target], timeout=8.0)

    def quit_app(self, target: str) -> None:
        self._script(f'tell application "{target}" to quit', timeout=6.0)

    # --- Système --------------------------------------------------------------

    def open_url(self, url: str) -> None:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
            # Sans schéma, `open` pourrait interpréter la chaîne comme un
            # chemin local : on impose http par défaut.
            url = f"https://{url}"
        self.run(["open", url], timeout=8.0)

    def open_path(self, path: str) -> None:
        self.run(["open", str(Path(path).expanduser())], timeout=8.0)

    def choose_path(self, kind: str) -> str:
        """Ouvre le sélecteur Finder natif et retourne un chemin POSIX."""
        commands = {
            "file": "POSIX path of (choose file)",
            "folder": "POSIX path of (choose folder)",
        }
        source = commands.get(kind)
        if source is None:
            raise Unsupported("type de sélection macOS inconnu")
        try:
            selected = self.run(["osascript", "-e", source], timeout=120.0).strip()
        except ActionFailed as error:
            if "-128" in str(error):
                raise SelectionCancelled from error
            raise
        if not selected:
            raise SelectionCancelled
        return selected

    def send_hotkey(self, combination: str) -> None:
        """Envoie une combinaison décrite sous la forme `cmd+shift+n`.

        L'analyse est déléguée au catalogue partagé : l'éditeur de
        configuration applique ainsi exactement la même règle, et une
        combinaison enregistrée est nécessairement exécutable.
        """
        try:
            hotkey = parse_hotkey(combination)
        except InvalidHotkey as error:
            raise ActionFailed(str(error)) from error

        using = ""
        if hotkey.modifiers:
            using = " using {" + ", ".join(
                modifier.mac for modifier in hotkey.modifiers
            ) + "}"

        if hotkey.key is not None:
            action = f"key code {hotkey.key.mac}"
        else:
            # `keystroke` envoie un caractère : AppleScript le résout selon la
            # disposition active, ce qui reste juste sur un clavier AZERTY.
            # Échappement du guillemet pour rester dans une chaîne AppleScript.
            safe = hotkey.character.replace("\\", "\\\\").replace('"', '\\"')
            action = f'keystroke "{safe}"'

        self._script(f'tell application "System Events" to {action}{using}')

    def lock_session(self) -> None:
        # Raccourci système de verrouillage immédiat.
        self._script(
            'tell application "System Events" to keystroke "q" using '
            "{command down, control down}"
        )

    def get_cpu(self) -> int | None:
        """Charge processeur approchée, dérivée de la charge moyenne système.

        `top -l 1` donnerait un pourcentage d'occupation exact mais coûte plus
        d'une demi-seconde, ce qui est inacceptable pour un tableau de bord
        rafraîchi en continu. `sysctl vm.loadavg` répond en quelques
        millisecondes ; rapportée au nombre de cœurs, la charge moyenne donne un
        indicateur suffisamment représentatif pour un affichage de supervision.
        """
        if self._cpu_count is None:
            raw_count = self._sysctl("hw.ncpu")
            try:
                self._cpu_count = max(1, int(raw_count)) if raw_count else 1
            except ValueError:
                self._cpu_count = 1

        raw = self._sysctl("vm.loadavg")
        if not raw:
            return None

        # Format : "{ 3,11 3,22 3,20 }" ou "{ 3.11 3.22 3.20 }" selon la locale.
        match = re.search(r"\{\s*([\d.,]+)", raw)
        if not match:
            return None

        load = _parse_number(match.group(1))
        if load is None:
            return None

        return max(0, min(100, int(round(load * 100.0 / self._cpu_count))))

    def _sysctl(self, key: str) -> str | None:
        try:
            return self.run(["sysctl", "-n", key], timeout=2.0).strip()
        except (Unsupported, ActionFailed):
            return None

    def snapshot(self) -> SystemSnapshot:
        """Collecte optimisée.

        Volume, sourdine, micro, application active et liste des applications
        sont obtenus par une seule requête AppleScript. Ces cinq valeurs
        demandaient autant d'appels séparés, chacun payant environ 170 ms de
        lancement de processus, ce qui se ressentait sur la fluidité du tableau
        de bord.
        """
        snapshot = SystemSnapshot()

        applications_script = (
            'tell application "System Events"\n'
            "  set fa to name of first application process whose frontmost is true\n"
            "  set al to name of every application process whose "
            "background only is false\n"
            "end tell\n"
            "set AppleScript's text item delimiters to \",\"\n"
            if self.feature_enabled("windows")
            else 'set fa to ""\nset al to ""\n'
        )
        script = (
            "set vs to (get volume settings)\n"
            "set ov to output volume of vs\n"
            "set om to output muted of vs\n"
            "set iv to input volume of vs\n"
            f"{applications_script}"
            'return (ov as text) & "|" & (om as text) & "|" & (iv as text) '
            '& "|" & fa & "|" & (al as text)'
        )

        raw = self._script_quiet(script)

        if raw is not None:
            fields = raw.split("|")
            if len(fields) >= 5:
                if fields[0].strip().isdigit():
                    snapshot.volume = max(0, min(100, int(fields[0].strip())))

                snapshot.muted = fields[1].strip() == "true"

                mic_raw = fields[2].strip()
                if mic_raw.isdigit():
                    snapshot.mic_muted = int(mic_raw) == 0
                else:
                    snapshot.mic_muted = self._mic_muted

                snapshot.active_app = fields[3].strip()

                snapshot.apps = _visible_apps(fields[4])
        else:
            # Repli sur les accesseurs unitaires si la requête groupée échoue.
            snapshot.volume = self.get_volume()
            snapshot.muted = self.is_muted()
            snapshot.mic_muted = self.is_mic_muted()
            snapshot.active_app = self.get_active_app()
            snapshot.apps = self.list_apps()

        if self.feature_enabled("media"):
            try:
                snapshot.media = self.get_media()
            except Exception:
                snapshot.media = None
            if (
                snapshot.media is not None
                and not self.feature_enabled("media_artwork")
            ):
                snapshot.media.art_url = ""

        # Le volume du lecteur a déjà été relevé par `get_media`, dans la même
        # requête AppleScript : aucun appel supplémentaire n'est nécessaire.
        if snapshot.media is not None:
            snapshot.app_volume = self._media.volume

        # CoreAudio répond en quelques millisecondes : la liste peut être
        # collectée à chaque cycle sans coût notable.
        if self.feature_enabled("audio_output"):
            try:
                devices = self._audio.outputs()
                snapshot.audio_outputs = [device.name for device in devices]
                snapshot.audio_output = next(
                    (device.name for device in devices if device.is_default), ""
                )
            except Exception:
                snapshot.audio_outputs = []
                snapshot.audio_output = ""

        # macOS conserve les notifications dans sa base interne ; le lecteur
        # reste isolé afin qu'un refus d'accès n'affecte pas le reste du relevé.
        if self.feature_enabled("notifications"):
            try:
                snapshot.notifications = self.list_notifications()
                snapshot.new_notification = self.take_new_notification()
            except Exception:
                snapshot.notifications = []
                snapshot.new_notification = None

        if self.feature_enabled("system_stats"):
            snapshot.cpu = self.get_cpu()
            snapshot.memory = self.get_memory()
        return snapshot

    def get_memory(self) -> int | None:
        try:
            output = self.run(["vm_stat"], timeout=3.0)
        except (Unsupported, ActionFailed):
            return None

        pages: dict[str, int] = {}
        for line in output.splitlines():
            match = re.match(r'^"?([^":]+)"?:\s+(\d+)\.?', line.strip())
            if match:
                pages[match.group(1).strip().lower()] = int(match.group(2))

        free = pages.get("pages free", 0) + pages.get("pages speculative", 0)
        active = pages.get("pages active", 0)
        inactive = pages.get("pages inactive", 0)
        wired = pages.get("pages wired down", 0)
        compressed = pages.get("pages occupied by compressor", 0)

        total = free + active + inactive + wired + compressed
        if total <= 0:
            return None

        used = active + wired + compressed
        return max(0, min(100, int(round(used * 100.0 / total))))

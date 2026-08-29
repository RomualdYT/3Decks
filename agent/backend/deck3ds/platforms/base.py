"""Contrat commun aux adaptateurs de plateforme.

Chaque système d'exploitation fournit une sous-classe. Les capacités réellement
disponibles varient : une méthode non supportée lève `Unsupported`, ce qui
remonte jusqu'à la 3DS sous forme de message d'échec explicite. Un bouton ne
doit jamais sembler fonctionner sans effet.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from dataclasses import fields as dataclass_fields


class Unsupported(Exception):
    """L'action n'est pas disponible sur cette plateforme ou cette machine."""


class ActionFailed(Exception):
    """L'action est supportée mais a échoué."""


class SelectionCancelled(Exception):
    """L'utilisateur a fermé un sélecteur natif sans choisir d'élément."""


@dataclass
class MediaInfo:
    """Média en cours de lecture."""

    title: str = ""
    artist: str = ""
    app: str = ""
    playing: bool = False
    album: str = ""
    #: Adresse de la pochette, si le lecteur en expose une.
    art_url: str = ""
    #: Position de lecture et durée, en secondes. `None` si inconnues.
    position: float | None = None
    duration: float | None = None

    def as_payload(self) -> dict[str, object] | None:
        if not self.title:
            return None

        payload: dict[str, object] = {
            "title": self.title,
            "artist": self.artist,
            "app": self.app,
            "playing": self.playing,
        }

        if self.album:
            payload["album"] = self.album

        # La position n'est transmise que si la durée est connue : sans elle,
        # la console ne pourrait pas dessiner de barre de progression.
        if self.duration is not None and self.duration > 0:
            payload["duration"] = int(self.duration)
            if self.position is not None:
                payload["position"] = max(
                    0, min(int(self.duration), int(self.position))
                )

        return payload


@dataclass
class NotificationInfo:
    """Notification du système, telle qu'affichée par la console."""

    app: str = ""
    title: str = ""
    body: str = ""
    icon: str = "star"
    age: int = 0

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


def _as_notification_info(entry: object) -> NotificationInfo:
    """Traduit une notification lue en base vers le format de l'interface.

    Le lecteur de notifications retient l'identifiant de l'application et une
    empreinte de déduplication, dont la console n'a pas l'usage : seuls les
    cinq champs affichés traversent cette frontière.
    """
    return NotificationInfo(
        app=entry.app,
        title=entry.title,
        body=entry.body,
        icon=entry.icon,
        age=entry.age,
    )


@dataclass(frozen=True)
class Capabilities:
    """Ce que l'adaptateur sait réellement faire sur cette machine.

    Sans cette déclaration, l'interface laisserait configurer des boutons
    inertes : sur Windows par exemple, la sélection de fenêtre n'est pas
    implémentée. Le bouton se poserait sans erreur et resterait sans effet, ce
    qui est le pire des deux mondes. Ici, l'interface peut prévenir avant.

    Chaque champ correspond à une famille d'actions, pas à une méthode : c'est
    la granularité utile pour l'utilisateur qui compose une page.
    """

    volume: bool = False
    mute: bool = False
    mic: bool = False
    #: Volume interne du lecteur, distinct du volume système.
    app_volume: bool = False
    audio_output: bool = False
    media: bool = False
    #: Pochette de l'album transmise à la console.
    media_artwork: bool = False
    #: Lancement et fermeture d'applications.
    apps: bool = False
    #: Énumération et sélection des fenêtres ouvertes.
    windows: bool = False
    hotkey: bool = False
    open_url: bool = False
    open_path: bool = False
    lock: bool = False
    notifications: bool = False
    #: Processeur et mémoire, pour le tableau de bord « system ».
    system_stats: bool = False
    #: Integration transversale, activee par la configuration et non par l'OS.
    obs: bool = False

    def as_payload(self) -> dict[str, bool]:
        return {field_name: getattr(self, field_name) for field_name in fields_of(self)}


def fields_of(instance: object) -> tuple[str, ...]:
    """Noms des champs d'une dataclass, dans l'ordre de déclaration."""
    return tuple(item.name for item in dataclass_fields(instance))


@dataclass
class SystemSnapshot:
    """Photographie de l'état du poste, envoyée à la 3DS."""

    volume: int | None = None
    muted: bool | None = None
    mic_muted: bool | None = None
    #: Volume interne du lecteur, distinct du volume système.
    app_volume: int | None = None
    #: Sortie audio active et sorties disponibles.
    audio_output: str = ""
    audio_outputs: list[str] = field(default_factory=list)
    media: MediaInfo | None = None
    #: Notifications récentes, de la plus récente à la plus ancienne.
    notifications: list[NotificationInfo] = field(default_factory=list)
    #: Notification venant d'arriver, à annoncer une seule fois.
    new_notification: NotificationInfo | None = None
    active_app: str = ""
    apps: list[str] = field(default_factory=list)
    cpu: int | None = None
    memory: int | None = None
    #: Détails du tableau de bord de performances. Chaque mesure reste
    #: facultative : les API disponibles diffèrent selon le matériel et l'OS.
    memory_used_mb: int | None = None
    memory_total_mb: int | None = None
    disk: int | None = None
    disk_free_mb: int | None = None
    disk_total_mb: int | None = None
    network_down_kbps: int | None = None
    network_up_kbps: int | None = None
    top_process: str = ""
    top_process_cpu: int | None = None
    gpu: int | None = None
    temperature: int | None = None

    def apply_performance(self, performance: PerformanceInfo) -> None:
        """Recopie une collecte groupée sans dupliquer sa liste de champs."""
        for field_name in fields_of(performance):
            setattr(self, field_name, getattr(performance, field_name))


@dataclass
class PerformanceInfo:
    """Mesures portables du poste, regroupées en une seule collecte.

    Les adaptateurs peuvent ainsi mutualiser les appels natifs coûteux. Un
    champ à ``None`` signifie « non exposé sur cette machine », ce qui permet à
    la console de composer sa vue sans inventer de valeur.
    """

    cpu: int | None = None
    memory: int | None = None
    memory_used_mb: int | None = None
    memory_total_mb: int | None = None
    disk: int | None = None
    disk_free_mb: int | None = None
    disk_total_mb: int | None = None
    network_down_kbps: int | None = None
    network_up_kbps: int | None = None
    top_process: str = ""
    top_process_cpu: int | None = None
    gpu: int | None = None
    temperature: int | None = None


class Platform:
    """Adaptateur de plateforme.

    Les implémentations doivent être tolérantes : une information indisponible
    vaut `None` plutôt qu'une exception, afin que le tableau de bord affiche
    « inconnu » au lieu de faire échouer la collecte entière.
    """

    name = "generique"

    def configure_features(self, features: object) -> None:
        """Applique les collectes activées sans coupler la plateforme au parseur."""
        self._features = features

    def feature_enabled(self, name: str) -> bool:
        """Retourne le choix utilisateur, vrai pour les anciens appelants."""
        features = getattr(self, "_features", None)
        return bool(getattr(features, name, True))

    # --- Capacités ------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        """Ce que cet adaptateur sait faire.

        L'adaptateur générique ne sait rien faire : c'est le comportement voulu
        pour une plateforme sans implémentation, afin que l'interface le dise
        clairement plutôt que de laisser croire le contraire.
        """
        return Capabilities()

    def notification_status(self) -> dict[str, object]:
        """État détaillé du fournisseur de notifications.

        Ce diagnostic complète le booléen de capacité : l'interface peut ainsi
        expliquer pourquoi les notifications sont absentes, sans exposer de
        détail propre à une plateforme dans son code.
        """
        return {
            "provider": "none",
            "available": False,
            "access": "Unavailable",
            "error": "",
        }

    def open_permission_settings(self, permission: str) -> None:
        """Ouvre le panneau système correspondant à une permission connue.

        Chaque adaptateur conserve sa propre liste blanche : une valeur venue
        du navigateur ne peut donc jamais devenir une commande arbitraire.
        """
        raise Unsupported("réglage d'autorisation indisponible")

    # --- Volume ---------------------------------------------------------------

    def get_volume(self) -> int | None:
        return None

    def set_volume(self, value: int) -> None:
        raise Unsupported("reglage du volume indisponible")

    def is_muted(self) -> bool | None:
        return None

    def set_muted(self, muted: bool) -> None:
        raise Unsupported("coupure du son indisponible")

    # --- Volume propre à une application -------------------------------------

    def get_app_volume(self) -> int | None:
        """Volume interne du lecteur, indépendant du volume système.

        Utile lorsque la musique sort sur une enceinte externe : le volume du
        système ne l'affecte alors plus, seul celui du lecteur agit.
        """
        return None

    def set_app_volume(self, value: int) -> None:
        raise Unsupported("volume de l'application indisponible")

    # --- Sortie audio ---------------------------------------------------------

    def get_audio_output(self) -> str:
        """Nom de la sortie audio active."""
        return ""

    def list_audio_outputs(self) -> list[str]:
        """Sorties audio disponibles."""
        return []

    def cycle_audio_output(self) -> str:
        raise Unsupported("changement de sortie indisponible")

    def select_audio_output(self, needle: str) -> str:
        raise Unsupported("changement de sortie indisponible")

    # --- Microphone -----------------------------------------------------------

    def is_mic_muted(self) -> bool | None:
        return None

    def set_mic_muted(self, muted: bool) -> None:
        raise Unsupported("controle du micro indisponible")

    # --- Média ----------------------------------------------------------------

    def get_media(self) -> MediaInfo | None:
        return None

    def media_play_pause(self) -> None:
        raise Unsupported("controle media indisponible")

    def media_next(self) -> None:
        raise Unsupported("controle media indisponible")

    def media_previous(self) -> None:
        raise Unsupported("controle media indisponible")

    # --- Applications ---------------------------------------------------------

    def get_active_app(self) -> str:
        return ""

    def list_apps(self) -> list[str]:
        return []

    def list_launchable_apps(self) -> list[str]:
        """Applications que l'utilisateur peut choisir dans l'éditeur.

        La liste des applications ouvertes reste un repli utile sur une
        plateforme qui ne sait pas parcourir les applications installées.
        """
        return self.list_apps()

    def list_windows(self) -> list[tuple[str, str]]:
        """Fenêtres ouvertes, sous forme de paires (application, titre).

        La plus en avant vient en premier.
        """
        return []

    def focus_window(self, app: str, title: str) -> str:
        """Ramène une fenêtre au premier plan. Retourne le libellé retenu."""
        raise Unsupported("selection de fenetre indisponible")

    def launch_app(self, target: str) -> None:
        raise Unsupported("lancement d'application indisponible")

    def quit_app(self, target: str) -> None:
        raise Unsupported("fermeture d'application indisponible")

    # --- Système --------------------------------------------------------------

    def open_url(self, url: str) -> None:
        raise Unsupported("ouverture d'URL indisponible")

    def open_path(self, path: str) -> None:
        raise Unsupported("ouverture de fichier indisponible")

    def choose_path(self, kind: str) -> str:
        """Demande au système de choisir un fichier ou un dossier existant."""
        raise Unsupported("sélecteur de fichier indisponible")

    def send_hotkey(self, keys: str) -> None:
        raise Unsupported("raccourcis clavier indisponibles")

    def lock_session(self) -> None:
        raise Unsupported("verrouillage indisponible")

    def list_notifications(self) -> list[NotificationInfo]:
        """Notifications récentes du système."""
        return []

    def take_new_notification(self) -> NotificationInfo | None:
        """Notification venant d'arriver, ou `None`.

        Ne la retourne qu'une seule fois : l'appelant peut donc l'annoncer sans
        risque de répétition.
        """
        return None

    # --- Notifications, lecture partagée --------------------------------------
    #
    # Chaque plateforme choisit sa source (SQLite sur macOS, WinRT sur Windows)
    # mais partage la conversion vers le format de la console et la détection
    # d'une nouveauté à annoncer.

    def _read_notifications(self) -> list[NotificationInfo]:
        """Notifications récentes, converties au format de l'interface.

        La détection de nouveauté est faite ici plutôt qu'à la demande : ainsi
        une notification arrivée entre deux collectes n'est jamais manquée.
        """
        entries = self._notifications.read()

        arrival = self._notifications.take_new(entries)
        if arrival is not None:
            self._pending_notification = _as_notification_info(arrival)

        return [_as_notification_info(entry) for entry in entries]

    def _take_pending_notification(self) -> NotificationInfo | None:
        pending = self._pending_notification
        self._pending_notification = None
        return pending

    def get_cpu(self) -> int | None:
        return None

    def get_memory(self) -> int | None:
        return None

    def get_performance(self) -> PerformanceInfo:
        """Collecte minimale, conservant les accesseurs historiques.

        Chaque valeur est isolée pour qu'un capteur défaillant ne masque pas
        l'autre. macOS et Windows remplacent cette méthode par une collecte
        groupée plus riche.
        """
        performance = PerformanceInfo()
        try:
            performance.cpu = self.get_cpu()
        except Exception:
            pass
        try:
            performance.memory = self.get_memory()
        except Exception:
            pass
        return performance

    # --- Collecte -------------------------------------------------------------

    def snapshot(self) -> SystemSnapshot:
        """Collecte l'état complet, en isolant chaque source de panne.

        Une seule information cassée ne doit pas priver le tableau de bord de
        toutes les autres.
        """
        snapshot = SystemSnapshot()

        def safe(getter, default=None):
            try:
                return getter()
            except Exception:
                return default

        snapshot.volume = safe(self.get_volume)
        snapshot.muted = safe(self.is_muted)
        snapshot.mic_muted = safe(self.is_mic_muted)
        if self.feature_enabled("media"):
            snapshot.media = safe(self.get_media)
            if snapshot.media is not None and not self.feature_enabled("media_artwork"):
                snapshot.media.art_url = ""
        if self.feature_enabled("windows"):
            snapshot.active_app = safe(self.get_active_app, "") or ""
            snapshot.apps = safe(self.list_apps, []) or []
        if self.feature_enabled("notifications"):
            snapshot.notifications = safe(self.list_notifications, []) or []
            snapshot.new_notification = safe(self.take_new_notification)
        if self.feature_enabled("system_stats"):
            performance = safe(self.get_performance, PerformanceInfo())
            snapshot.apply_performance(performance)
        return snapshot

    # --- Utilitaires partagés -------------------------------------------------

    @staticmethod
    def run(
        command: list[str],
        timeout: float = 5.0,
        check: bool = True,
    ) -> str:
        """Exécute un programme et retourne sa sortie standard.

        La liste d'arguments est passée telle quelle, sans shell : aucune
        interpolation n'est possible, ce qui élimine l'injection de commande.
        """
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as error:
            raise Unsupported(f"{command[0]} introuvable") from error
        except subprocess.TimeoutExpired as error:
            raise ActionFailed(f"{command[0]} n'a pas repondu") from error

        if check and completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            # Un message court reste lisible sur l'écran de la console.
            raise ActionFailed(detail.splitlines()[0][:80] if detail else "echec")

        return completed.stdout

    @staticmethod
    def spawn(command: list[str]) -> None:
        """Lance un programme sans attendre sa fin."""
        try:
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError as error:
            raise Unsupported(f"{command[0]} introuvable") from error
        except OSError as error:
            raise ActionFailed(str(error)) from error

from __future__ import annotations

import tempfile
from pathlib import Path


from deck3ds import config as config_module
from deck3ds.platforms.base import (
    ActionFailed,
    MediaInfo,
    Platform,
    Unsupported,
)


class FakePlatform(Platform):
    """Plateforme simulée : mémorise l'état et journalise les appels."""

    name = "fake"

    def __init__(self) -> None:
        self.volume = 40
        self.muted = False
        self.mic_muted = False
        self.app_volume: int | None = 30
        self.outputs = ["Haut-parleurs", "Enceinte", "Casque"]
        self.output_index = 0
        self.calls: list[str] = []
        self.fail_next: str | None = None

    def get_app_volume(self):
        return self.app_volume

    def set_app_volume(self, value):
        self._maybe_fail("set_app_volume")
        self.calls.append(f"set_app_volume:{value}")
        self.app_volume = max(0, min(100, int(value)))

    # --- Sortie audio ---

    def get_audio_output(self):
        return self.outputs[self.output_index]

    def list_audio_outputs(self):
        return list(self.outputs)

    def cycle_audio_output(self):
        self.output_index = (self.output_index + 1) % len(self.outputs)
        self.calls.append(f"cycle_output:{self.get_audio_output()}")
        return self.get_audio_output()

    def select_audio_output(self, needle):
        for index, name in enumerate(self.outputs):
            if needle.lower() in name.lower():
                self.output_index = index
                self.calls.append(f"select_output:{name}")
                return name
        raise ActionFailed(f"sortie introuvable : {needle}")

    def _maybe_fail(self, name: str) -> None:
        if self.fail_next == name:
            self.fail_next = None
            raise ActionFailed(f"echec simule de {name}")

    def get_volume(self):
        return self.volume

    def set_volume(self, value):
        self._maybe_fail("set_volume")
        self.calls.append(f"set_volume:{value}")
        self.volume = max(0, min(100, int(value)))

    def is_muted(self):
        return self.muted

    def set_muted(self, muted):
        self.calls.append(f"set_muted:{muted}")
        self.muted = muted

    def is_mic_muted(self):
        return self.mic_muted

    def set_mic_muted(self, muted):
        self.calls.append(f"set_mic:{muted}")
        self.mic_muted = muted

    def get_media(self):
        return MediaInfo("Titre", "Artiste", "FauxLecteur", True)

    def media_play_pause(self):
        self.calls.append("play_pause")

    def media_next(self):
        self.calls.append("next")

    def media_previous(self):
        self.calls.append("previous")

    def get_active_app(self):
        return "Terminal"

    def list_apps(self):
        return ["Terminal", "Safari"]

    def launch_app(self, target):
        self._maybe_fail("launch_app")
        self.calls.append(f"launch:{target}")

    def list_windows(self):
        return [("Safari", "Page"), ("Terminal", "shell")]

    def focus_window(self, app, title):
        self.calls.append(f"focus:{app}|{title}")
        return title or app

    def quit_app(self, target):
        self.calls.append(f"quit:{target}")

    def open_url(self, url):
        self.calls.append(f"url:{url}")

    def open_path(self, path):
        self.calls.append(f"path:{path}")

    def send_hotkey(self, keys):
        self.calls.append(f"hotkey:{keys}")

    def lock_session(self):
        self.calls.append("lock")

    def get_cpu(self):
        return 25

    def get_memory(self):
        return 50

    def spawn(self, command):
        self.calls.append("spawn:" + " ".join(command))


# --- Protocole ----------------------------------------------------------------


def minimal_config(**overrides):
    base = {
        "pages": [
            {
                "id": "main",
                "title": "Principal",
                "buttons": [{"id": "b1", "slot": 0, "label": "Un", "action": "noop"}],
            }
        ]
    }
    base.update(overrides)
    return base


def _mac_platform(player_running=True, **scripts):
    """Instancie `MacPlatform` sans toucher au système.

    `__init__` construit des objets CoreAudio et lit le centre de
    notifications : on l'évite avec `__new__` puis on injecte le strict
    nécessaire. Les scripts AppleScript ne sont jamais exécutés : ils sont
    interceptés et confrontés à un dictionnaire de réponses, dont les clés
    sont des fragments recherchés dans le source du script.

    `player_running` répond au test de présence que `get_media` effectue
    avant d'interroger un lecteur.
    """
    from deck3ds.platforms.macos import MacPlatform
    from deck3ds.platforms.macos_media import MacMediaProvider

    platform = MacPlatform.__new__(MacPlatform)
    platform._mic_muted = None
    platform._mic_restore = 75
    platform._cpu_count = 4
    platform.scripts = []

    def run_script(source, timeout=None):
        platform.scripts.append(source)
        # Le script porte sa propre garde de présence : un lecteur arrêté
        # renvoie une chaîne vide sans que le reste ne s'exécute. Le simuler
        # fidèlement permet aux tests de détecter la perte de cette garde.
        if "is not running" in source and not player_running:
            return ""
        for fragment, reply in scripts.items():
            if fragment in source:
                if isinstance(reply, BaseException):
                    raise reply
                return reply
        if "is running" in source:
            return "true" if player_running else "false"
        return ""

    def quiet(source, *args):
        # Le vrai `_script_quiet` avale les erreurs et retourne None.
        try:
            return run_script(source)
        except (Unsupported, ActionFailed):
            return None

    platform._script = run_script
    platform._script_quiet = quiet
    platform._media = MacMediaProvider(
        platform._script, platform._script_quiet, platform.feature_enabled
    )
    return platform


def demo_config():
    from deck3ds.configuration.location import initialize

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "config.json"
        initialize(path)
        return config_module.load(path)

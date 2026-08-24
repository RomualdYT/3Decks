"""Exécution des actions.

La 3DS n'envoie qu'un identifiant de page et de bouton. C'est ici, et
uniquement ici, que l'on décide quoi exécuter, en consultant la configuration
locale. La console ne transmet jamais de commande à lancer.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

from dataclasses import dataclass

from .config import Action, ButtonConfig, Config
from .messages import msg
from .obs import ObsClient, ObsError
from .platforms.base import ActionFailed, Platform, Unsupported


@dataclass
class ActionOutcome:
    ok: bool
    message: str = ""
    open_page: str | None = None
    #: Vrai si l'état du poste a probablement changé, ce qui justifie un
    #: rafraîchissement immédiat du tableau de bord.
    state_changed: bool = False
    #: Vrai si l'effet met plusieurs secondes à devenir observable, comme une
    #: commande de lecture envoyée à un lecteur diffusant sur une enceinte.
    slow_effect: bool = False
    #: Demande à la console d'ouvrir son écran de réglages.
    open_settings: bool = False
    #: Demande à la console d'ouvrir son panneau de volumes.
    open_modal: bool = False
    #: Demande à la console de basculer en plein écran.
    toggle_frame: bool = False


class Dispatcher:
    def __init__(self, platform: Platform, config: Config) -> None:
        self.platform = platform
        self.config = config

    def set_config(self, config: Config) -> None:
        self.config = config

    def run_button(self, button: ButtonConfig, hold: bool) -> ActionOutcome:
        action = button.hold_action if hold else button.action

        if action is None:
            # Un appui long sans action dédiée ne doit pas rejouer l'action
            # principale : cela produirait un effet inattendu.
            return ActionOutcome(True, "")

        return self.run(action)

    def run(self, action: Action) -> ActionOutcome:
        handler = getattr(self, f"_do_{action.kind.replace('.', '_')}", None)
        if handler is None:
            return ActionOutcome(False, msg("unhandled", kind=action.kind))

        try:
            return handler(action.args)
        except Unsupported as error:
            return ActionOutcome(False, str(error))
        except ActionFailed as error:
            return ActionOutcome(False, str(error))
        except ObsError as error:
            return ActionOutcome(False, str(error))
        except Exception as error:  # filet de sécurité
            # Un imprévu ne doit jamais interrompre le serveur : on le remonte
            # comme un échec d'action ordinaire.
            return ActionOutcome(False, msg("error", kind=type(error).__name__))

    # --- Volume ---------------------------------------------------------------

    def _adjust_volume(self, delta: int) -> ActionOutcome:
        """Ajuste le volume relativement à sa valeur courante.

        Si le niveau n'est pas lisible, on applique quand même la variation en
        partant d'une estimation : mieux vaut un ajustement approximatif qu'un
        bouton inopérant. Le tableau de bord affichera ensuite la valeur réelle.
        """
        current = self.platform.get_volume()

        if current is None:
            self.platform.set_volume(50 + delta)
            return ActionOutcome(True, msg("volume_adjusted"), state_changed=True)

        target = max(0, min(100, current + delta))
        self.platform.set_volume(target)
        return ActionOutcome(True, msg("volume_set", value=target), state_changed=True)

    def _do_volume_up(self, args: dict) -> ActionOutcome:
        step = int(args.get("step", self.config.volume_step))
        return self._adjust_volume(abs(step))

    def _do_volume_down(self, args: dict) -> ActionOutcome:
        step = int(args.get("step", self.config.volume_step))
        return self._adjust_volume(-abs(step))

    def _do_volume_set(self, args: dict) -> ActionOutcome:
        value = int(args.get("value", 50))
        value = max(0, min(100, value))
        self.platform.set_volume(value)
        return ActionOutcome(True, msg("volume_set", value=value), state_changed=True)

    # --- Volume du lecteur ----------------------------------------------------

    def _adjust_app_volume(self, delta: int) -> ActionOutcome:
        current = self.platform.get_app_volume()
        if current is None:
            raise Unsupported(msg("app_volume_unreadable"))

        target = max(0, min(100, current + delta))
        self.platform.set_app_volume(target)
        return ActionOutcome(True, msg("music_set", value=target), state_changed=True)

    def _do_app_volume_up(self, args: dict) -> ActionOutcome:
        step = int(args.get("step", self.config.volume_step))
        return self._adjust_app_volume(abs(step))

    def _do_app_volume_down(self, args: dict) -> ActionOutcome:
        step = int(args.get("step", self.config.volume_step))
        return self._adjust_app_volume(-abs(step))

    def _do_app_volume_set(self, args: dict) -> ActionOutcome:
        value = max(0, min(100, int(args.get("value", 50))))
        self.platform.set_app_volume(value)
        return ActionOutcome(True, msg("music_set", value=value), state_changed=True)

    def _do_volume_mute_toggle(self, args: dict) -> ActionOutcome:
        del args
        current = self.platform.is_muted()
        target = not bool(current)
        self.platform.set_muted(target)
        return ActionOutcome(
            True, msg("sound_muted") if target else msg("sound_restored"), state_changed=True
        )

    # --- Sortie audio ---------------------------------------------------------

    def _do_audio_output_cycle(self, args: dict) -> ActionOutcome:
        del args
        name = self.platform.cycle_audio_output()
        return ActionOutcome(True, name, state_changed=True)

    def _do_audio_output_set(self, args: dict) -> ActionOutcome:
        target = str(args.get("target", ""))
        if not target:
            return ActionOutcome(False, msg("missing_output"))
        name = self.platform.select_audio_output(target)
        return ActionOutcome(True, name, state_changed=True)

    # --- Microphone -----------------------------------------------------------

    def _do_mic_mute_toggle(self, args: dict) -> ActionOutcome:
        del args
        current = self.platform.is_mic_muted()
        target = not bool(current)
        self.platform.set_mic_muted(target)
        return ActionOutcome(
            True, msg("mic_muted") if target else msg("mic_active"), state_changed=True
        )

    def _do_mic_mute(self, args: dict) -> ActionOutcome:
        del args
        self.platform.set_mic_muted(True)
        return ActionOutcome(True, msg("mic_muted"), state_changed=True)

    def _do_mic_unmute(self, args: dict) -> ActionOutcome:
        del args
        self.platform.set_mic_muted(False)
        return ActionOutcome(True, msg("mic_active"), state_changed=True)

    # --- Média ----------------------------------------------------------------

    def _do_media_play_pause(self, args: dict) -> ActionOutcome:
        del args
        self.platform.media_play_pause()
        return ActionOutcome(
            True, msg("play_pause"), state_changed=True, slow_effect=True
        )

    def _do_media_next(self, args: dict) -> ActionOutcome:
        del args
        self.platform.media_next()
        return ActionOutcome(
            True, msg("next_track"), state_changed=True, slow_effect=True
        )

    def _do_media_previous(self, args: dict) -> ActionOutcome:
        del args
        self.platform.media_previous()
        return ActionOutcome(
            True, msg("previous_track"), state_changed=True, slow_effect=True
        )

    # --- Applications ---------------------------------------------------------

    def _do_app_launch(self, args: dict) -> ActionOutcome:
        target = str(args.get("target", ""))
        if not target:
            return ActionOutcome(False, msg("missing_target"))
        self.platform.launch_app(target)
        return ActionOutcome(True, target, state_changed=True)

    def _do_window_focus(self, args: dict) -> ActionOutcome:
        """Ramène au premier plan une fenêtre choisie sur la console.

        L'identification passe par le couple application et titre plutôt que par
        un numéro de fenêtre : les numéros changent au fil des ouvertures, alors
        que ce couple reste stable entre l'affichage de la liste et l'appui.
        """
        app = str(args.get("app", ""))
        title = str(args.get("title", ""))

        if not app:
            return ActionOutcome(False, msg("missing_window"))

        label = self.platform.focus_window(app, title)
        return ActionOutcome(True, label, state_changed=True)

    def _do_app_quit(self, args: dict) -> ActionOutcome:
        target = str(args.get("target", ""))
        if not target:
            return ActionOutcome(False, msg("missing_target"))
        self.platform.quit_app(target)
        return ActionOutcome(True, msg("app_closed", target=target), state_changed=True)

    # --- Système --------------------------------------------------------------

    def _do_url_open(self, args: dict) -> ActionOutcome:
        url = str(args.get("url", ""))
        if not url:
            return ActionOutcome(False, msg("missing_url"))
        self.platform.open_url(url)
        return ActionOutcome(True, msg("link_opened"), state_changed=True)

    def _do_path_open(self, args: dict) -> ActionOutcome:
        path = str(args.get("path", ""))
        if not path:
            return ActionOutcome(False, msg("missing_path"))
        self.platform.open_path(path)
        return ActionOutcome(True, msg("opened"), state_changed=True)

    def _do_hotkey(self, args: dict) -> ActionOutcome:
        keys = str(args.get("keys", ""))
        if not keys:
            return ActionOutcome(False, msg("missing_keys"))
        self.platform.send_hotkey(keys)
        return ActionOutcome(True, keys)

    def _do_script_run(self, args: dict) -> ActionOutcome:
        name = str(args.get("script", ""))
        command = self.config.scripts.get(name)
        if not command:
            # La liste blanche est la seule source autorisée : un nom absent est
            # refusé, jamais interprété.
            return ActionOutcome(False, msg("unknown_script", name=name))

        self.platform.spawn(command)
        return ActionOutcome(True, name, state_changed=True)

    def _do_page_open(self, args: dict) -> ActionOutcome:
        page = str(args.get("page", ""))
        if not page:
            return ActionOutcome(False, msg("missing_page"))
        return ActionOutcome(True, "", open_page=page)

    def _do_system_lock(self, args: dict) -> ActionOutcome:
        del args
        self.platform.lock_session()
        return ActionOutcome(True, msg("locked"))

    # --- OBS Studio -----------------------------------------------------------

    def _obs(self) -> ObsClient:
        if not self.config.obs.enabled:
            raise ObsError(msg("obs_disabled"))
        return ObsClient(self.config.obs)

    def _do_obs_scene_set(self, args: dict) -> ActionOutcome:
        scene = str(args.get("scene", "")).strip()
        if not scene:
            return ActionOutcome(False, msg("obs_missing_scene"))
        with self._obs() as client:
            client.request("SetCurrentProgramScene", {"sceneName": scene})
        return ActionOutcome(True, msg("obs_scene_set", scene=scene), state_changed=True)

    def _do_obs_stream_toggle(self, args: dict) -> ActionOutcome:
        del args
        with self._obs() as client:
            client.request("ToggleStream")
        return ActionOutcome(True, msg("obs_stream_toggled"), state_changed=True)

    def _do_obs_record_toggle(self, args: dict) -> ActionOutcome:
        del args
        with self._obs() as client:
            client.request("ToggleRecord")
        return ActionOutcome(True, msg("obs_record_toggled"), state_changed=True)

    def _do_obs_source_toggle(self, args: dict) -> ActionOutcome:
        scene = str(args.get("scene", "")).strip()
        source = str(args.get("source", "")).strip()
        if not scene:
            return ActionOutcome(False, msg("obs_missing_scene"))
        if not source:
            return ActionOutcome(False, msg("obs_missing_source"))

        with self._obs() as client:
            item = client.request(
                "GetSceneItemId", {"sceneName": scene, "sourceName": source}
            )
            item_id = item.get("sceneItemId")
            if not isinstance(item_id, int):
                raise ObsError("OBS n'a pas renvoye l'identifiant de la source")
            enabled = client.request(
                "GetSceneItemEnabled",
                {"sceneName": scene, "sceneItemId": item_id},
            ).get("sceneItemEnabled")
            if not isinstance(enabled, bool):
                raise ObsError("OBS n'a pas renvoye l'etat de la source")
            client.request(
                "SetSceneItemEnabled",
                {
                    "sceneName": scene,
                    "sceneItemId": item_id,
                    "sceneItemEnabled": not enabled,
                },
            )
        return ActionOutcome(
            True, msg("obs_source_toggled", source=source), state_changed=True
        )

    def _do_settings_open(self, args: dict) -> ActionOutcome:
        """Demande à la console d'afficher ses réglages.

        Rien n'est exécuté sur l'ordinateur : seul l'indicateur transmis dans la
        réponse compte, la console se charge du reste.
        """
        del args
        return ActionOutcome(True, "", open_settings=True)

    def _do_modal_volumes(self, args: dict) -> ActionOutcome:
        """Demande l'ouverture du panneau de volumes sur la console.

        Rien n'est exécuté sur l'ordinateur : l'affichage appartient à la
        console, qui connaît déjà les valeurs courantes.
        """
        del args
        return ActionOutcome(True, "", open_modal=True)

    def _do_frame_toggle(self, args: dict) -> ActionOutcome:
        del args
        return ActionOutcome(True, "", toggle_frame=True)

    def _do_noop(self, args: dict) -> ActionOutcome:
        del args
        return ActionOutcome(True, "")

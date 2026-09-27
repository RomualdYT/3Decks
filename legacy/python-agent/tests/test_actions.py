from __future__ import annotations

import unittest
from unittest.mock import patch


from deck3ds import config as config_module
from deck3ds.actions import Dispatcher
from deck3ds.platforms.base import (
    Platform,
)


from .fixtures import FakePlatform, minimal_config


class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.platform = FakePlatform()
        self.config = config_module.parse(
            minimal_config(scripts={"build": ["echo", "ok"]})
        )
        self.dispatcher = Dispatcher(self.platform, self.config)

    def run_action(self, kind, **args):
        return self.dispatcher.run(config_module.Action(kind, args))

    def test_volume_relatif(self):
        self.platform.volume = 40
        outcome = self.run_action("volume.up", step=5)
        self.assertTrue(outcome.ok)
        self.assertEqual(self.platform.volume, 45)
        self.assertTrue(outcome.state_changed)

    def test_volume_borne_haute(self):
        self.platform.volume = 98
        self.run_action("volume.up", step=10)
        self.assertEqual(self.platform.volume, 100)

    def test_volume_borne_basse(self):
        self.platform.volume = 3
        self.run_action("volume.down", step=10)
        self.assertEqual(self.platform.volume, 0)

    def test_volume_pas_negatif_traite_en_absolu(self):
        """Un pas négatif sur volume.up ne doit pas baisser le son."""
        self.platform.volume = 50
        self.run_action("volume.up", step=-5)
        self.assertEqual(self.platform.volume, 55)

    def test_volume_set_borne(self):
        self.run_action("volume.set", value=500)
        self.assertEqual(self.platform.volume, 100)

    def test_volume_application_independant(self):
        """Régler la musique ne doit pas toucher au volume système."""
        self.platform.volume = 65
        self.platform.app_volume = 30

        outcome = self.run_action("app_volume.up", step=7)

        self.assertTrue(outcome.ok)
        self.assertEqual(self.platform.app_volume, 37)
        self.assertEqual(self.platform.volume, 65, "le volume PC a bouge")

    def test_volume_application_bornes(self):
        self.platform.app_volume = 97
        self.run_action("app_volume.up", step=10)
        self.assertEqual(self.platform.app_volume, 100)

        self.platform.app_volume = 4
        self.run_action("app_volume.down", step=10)
        self.assertEqual(self.platform.app_volume, 0)

    def test_volume_application_set(self):
        self.run_action("app_volume.set", value=250)
        self.assertEqual(self.platform.app_volume, 100)

    def test_volume_application_absent(self):
        """Sans lecteur pilotable, l'action échoue avec un message clair."""
        self.platform.app_volume = None
        outcome = self.run_action("app_volume.up")
        self.assertFalse(outcome.ok)
        self.assertTrue(outcome.message)

    def test_bascule_micro(self):
        self.platform.mic_muted = False
        self.run_action("mic.mute_toggle")
        self.assertTrue(self.platform.mic_muted)
        self.run_action("mic.mute_toggle")
        self.assertFalse(self.platform.mic_muted)

    def test_bascule_son(self):
        self.run_action("volume.mute_toggle")
        self.assertTrue(self.platform.muted)

    def test_media(self):
        self.run_action("media.play_pause")
        self.run_action("media.next")
        self.run_action("media.previous")
        self.assertEqual(self.platform.calls, ["play_pause", "next", "previous"])

    def test_media_signale_effet_lent(self):
        """La diffusion vers une enceinte demande une confirmation différée."""
        for action in ("media.play_pause", "media.next", "media.previous"):
            outcome = self.run_action(action)
            self.assertTrue(outcome.slow_effect, action)

    def test_volume_ne_signale_pas_effet_lent(self):
        """Le volume est immédiat : pas de relecture différée inutile."""
        self.assertFalse(self.run_action("volume.up").slow_effect)

    def test_sortie_audio_cycle(self):
        outcome = self.run_action("audio_output.cycle")
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.message, "Enceinte")
        self.assertTrue(outcome.state_changed)

    def test_sortie_audio_selection(self):
        outcome = self.run_action("audio_output.set", target="Casque")
        self.assertTrue(outcome.ok)
        self.assertIn("Casque", outcome.message)

    def test_sortie_audio_introuvable(self):
        outcome = self.run_action("audio_output.set", target="Inexistant")
        self.assertFalse(outcome.ok)
        self.assertTrue(outcome.message)

    def test_sortie_audio_cible_manquante(self):
        outcome = self.run_action("audio_output.set")
        self.assertFalse(outcome.ok)

    def test_selection_fenetre(self):
        outcome = self.run_action("window.focus", app="Safari", title="Page")
        self.assertTrue(outcome.ok)
        self.assertIn("focus:Safari|Page", self.platform.calls)

    def test_selection_fenetre_sans_application(self):
        outcome = self.run_action("window.focus", title="Page")
        self.assertFalse(outcome.ok)
        self.assertEqual(self.platform.calls, [])

    def test_lancement_application(self):
        outcome = self.run_action("app.launch", target="Safari")
        self.assertTrue(outcome.ok)
        self.assertIn("launch:Safari", self.platform.calls)

    def test_page_open_renvoie_navigation(self):
        outcome = self.run_action("page.open", page="music")
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.open_page, "music")

    def test_script_liste_blanche(self):
        outcome = self.run_action("script.run", script="build")
        self.assertTrue(outcome.ok)
        self.assertIn("spawn:echo ok", self.platform.calls)

    def test_script_hors_liste_refuse(self):
        outcome = self.run_action("script.run", script="rm-rf")
        self.assertFalse(outcome.ok)
        # Le message dépend de la langue : on vérifie qu'il nomme le script
        # fautif plutôt qu'un mot précis.
        self.assertIn("rm-rf", outcome.message)
        self.assertEqual(self.platform.calls, [])

    def test_echec_plateforme_remonte(self):
        self.platform.fail_next = "launch_app"
        outcome = self.run_action("app.launch", target="Safari")
        self.assertFalse(outcome.ok)
        self.assertIn("echec simule", outcome.message)

    def test_action_non_supportee(self):
        class Bare(Platform):
            pass

        dispatcher = Dispatcher(Bare(), self.config)
        outcome = dispatcher.run(config_module.Action("mic.mute_toggle", {}))
        self.assertFalse(outcome.ok)
        self.assertTrue(outcome.message)

    def test_exception_inattendue_ne_propage_pas(self):
        class Broken(Platform):
            def is_mic_muted(self):
                return False

            def set_mic_muted(self, muted):
                raise RuntimeError("boum")

        dispatcher = Dispatcher(Broken(), self.config)
        outcome = dispatcher.run(config_module.Action("mic.mute_toggle", {}))
        self.assertFalse(outcome.ok)
        self.assertIn("RuntimeError", outcome.message)

    def test_appui_long_sans_action_ne_rejoue_pas(self):
        button = self.config.pages[0].buttons[0]
        self.dispatcher.run_button(button, hold=True)
        self.assertEqual(self.platform.calls, [])

    def test_snapshot_isole_les_pannes(self):
        """Une source cassée ne doit pas priver le reste des données."""

        class PartlyBroken(FakePlatform):
            def get_cpu(self):
                raise RuntimeError("capteur casse")

        snapshot = PartlyBroken().snapshot()
        self.assertIsNone(snapshot.cpu)
        self.assertEqual(snapshot.volume, 40)
        self.assertEqual(snapshot.active_app, "Terminal")

    def test_obs_refuse_quand_integration_desactivee(self):
        outcome = self.run_action("obs.scene.set", scene="Direct")
        self.assertFalse(outcome.ok)
        self.assertTrue(outcome.message)

    def test_obs_change_de_scene(self):
        requests = []

        class FakeObsClient:
            def __init__(self, config):
                self.config = config

            def __enter__(self):
                return self

            def __exit__(self, *unused):
                return None

            def request(self, kind, data=None):
                requests.append((kind, data))
                return {}

        self.config.obs.enabled = True
        with patch("deck3ds.actions.ObsClient", FakeObsClient):
            outcome = self.run_action("obs.scene.set", scene="Direct")

        self.assertTrue(outcome.ok)
        self.assertEqual(
            requests,
            [("SetCurrentProgramScene", {"sceneName": "Direct"})],
        )

    def test_obs_bascule_une_source(self):
        requests = []

        class FakeObsClient:
            def __init__(self, config):
                self.config = config

            def __enter__(self):
                return self

            def __exit__(self, *unused):
                return None

            def request(self, kind, data=None):
                requests.append((kind, data))
                if kind == "GetSceneItemId":
                    return {"sceneItemId": 42}
                if kind == "GetSceneItemEnabled":
                    return {"sceneItemEnabled": True}
                return {}

        self.config.obs.enabled = True
        with patch("deck3ds.actions.ObsClient", FakeObsClient):
            outcome = self.run_action(
                "obs.source.toggle", scene="Direct", source="Camera"
            )

        self.assertTrue(outcome.ok)
        self.assertEqual(
            requests[-1],
            (
                "SetSceneItemEnabled",
                {
                    "sceneName": "Direct",
                    "sceneItemId": 42,
                    "sceneItemEnabled": False,
                },
            ),
        )

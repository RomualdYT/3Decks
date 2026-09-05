from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


from deck3ds import config as config_module
from deck3ds.server import Server


from .fixtures import FakePlatform, minimal_config, demo_config


class TestConfig(unittest.TestCase):
    def test_minimal_valide(self):
        parsed = config_module.parse(minimal_config())
        self.assertEqual(len(parsed.pages), 1)
        self.assertEqual(parsed.pages[0].buttons[0].id, "b1")

    def test_config_livree_valide(self):
        """La configuration fournie avec le projet doit être valide."""
        parsed = demo_config()
        self.assertGreaterEqual(len(parsed.pages), 1)

    def test_fonctionnalites_optionnelles_sont_persistantes(self):
        raw = minimal_config()
        raw["features"] = {"notifications": False, "apple_music": False}
        parsed = config_module.parse(raw)
        self.assertFalse(parsed.features.notifications)
        self.assertFalse(parsed.features.apple_music)
        self.assertTrue(parsed.features.spotify)
        rewritten = config_module.to_raw(parsed)
        self.assertFalse(rewritten["features"]["notifications"])
        self.assertFalse(rewritten["features"]["apple_music"])

    def test_fonctionnalite_inconnue_est_rejetee(self):
        raw = minimal_config()
        raw["features"] = {"telepathie": True}
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_fonctionnalite_exige_un_booleen(self):
        raw = minimal_config()
        raw["features"] = {"notifications": "oui"}
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

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

    def test_arguments_inconnus_refuses(self):
        for action in (
            {"type": "noop", "typo": True},
            {"type": "app.launch", "target": "Safari", "targte": "Terminal"},
        ):
            raw = minimal_config()
            raw["pages"][0]["buttons"][0]["action"] = action
            with self.subTest(action=action), self.assertRaises(config_module.ConfigError):
                config_module.parse(raw)

    def test_types_et_bornes_numeriques_du_catalogue(self):
        for value in (True, "50", -1, 101, float("nan"), float("inf")):
            raw = minimal_config()
            raw["pages"][0]["buttons"][0]["action"] = {
                "type": "volume.set",
                "value": value,
            }
            with self.subTest(value=value), self.assertRaises(config_module.ConfigError):
                config_module.parse(raw)

    def test_pas_de_volume_optionnel_et_borne(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["action"] = {
            "type": "volume.up",
            "step": 7,
        }
        self.assertEqual(
            config_module.parse(raw).pages[0].buttons[0].action.args["step"], 7
        )
        raw["pages"][0]["buttons"][0]["action"]["step"] = 51
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def test_chaine_action_stricte_et_url_http_normalisee(self):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["action"] = {
            "type": "app.launch",
            "target": {"unexpected": "object"},
        }
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

        raw["pages"][0]["buttons"][0]["action"] = {
            "type": "url.open",
            "url": "example.test/path",
        }
        parsed = config_module.parse(raw)
        self.assertEqual(
            parsed.pages[0].buttons[0].action.args["url"],
            "https://example.test/path",
        )
        raw["pages"][0]["buttons"][0]["action"]["url"] = "file:///etc/passwd"
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(raw)

    def _with_hotkey(self, combination):
        raw = minimal_config()
        raw["pages"][0]["buttons"][0]["action"] = {
            "type": "hotkey",
            "keys": combination,
        }
        return raw

    def test_raccourci_invalide_refuse_a_l_enregistrement(self):
        """Reject invalid shortcuts before installing a configuration."""
        for combination in ("nimportequoi", "ctrl+alt+banane", "", "cmd", "a+b", "f13"):
            with self.assertRaises(config_module.ConfigError, msg=combination):
                config_module.parse(self._with_hotkey(combination))

    def test_message_de_raccourci_situe_le_bouton(self):
        """Sans le chemin, l'utilisateur devrait chercher le bouton fautif."""
        with self.assertRaises(config_module.ConfigError) as ctx:
            config_module.parse(self._with_hotkey("ctrl+alt+banane"))
        message = str(ctx.exception)
        self.assertIn("keys", message)
        self.assertIn("banane", message)

    def test_raccourci_enregistre_sous_forme_normalisee(self):
        """Deux écritures d'un même raccourci ne doivent pas coexister."""
        config = config_module.parse(self._with_hotkey("shift+cmd+a"))
        self.assertEqual(config.pages[0].buttons[0].action.args["keys"], "cmd+shift+a")

    def test_graphies_historiques_toujours_acceptees(self):
        """Les configurations déjà écrites ne doivent pas devenir invalides."""
        for ancien, attendu in (
            ("echap", "escape"),
            ("entree", "return"),
            ("espace", "space"),
            ("cmd+shift+4", "cmd+shift+4"),
        ):
            config = config_module.parse(self._with_hotkey(ancien))
            self.assertEqual(
                config.pages[0].buttons[0].action.args["keys"], attendu, ancien
            )

    def test_raccourci_valide_survit_a_une_reecriture(self):
        """L'éditeur relit ce qu'il écrit : la forme doit être stable."""
        config = config_module.parse(self._with_hotkey("cmd+shift+escape"))
        rewritten = config_module.parse(config_module.to_raw(config))
        self.assertEqual(
            rewritten.pages[0].buttons[0].action.args["keys"], "cmd+shift+escape"
        )

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
            "pages": [{"id": f"p{i}", "title": "T", "buttons": []} for i in range(13)]
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
        parsed = demo_config()

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

    def test_sections_objets_refusent_une_liste_vide(self):
        """Une valeur vide ne doit pas contourner le contrôle de type."""
        for section in ("server", "integrations", "scripts"):
            with self.subTest(section=section):
                with self.assertRaises(config_module.ConfigError):
                    config_module.parse(minimal_config(**{section: []}))

    def test_booleen_refuse_pour_entier(self):
        """True est un entier en Python : le piège doit être détecté."""
        with self.assertRaises(config_module.ConfigError):
            config_module.parse(minimal_config(server={"port": True}))

    def test_json_invalide_message_clair(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
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

    def test_boutons_dynamiques_absents_de_la_configuration_serialisee(self):
        raw = minimal_config()
        raw["pages"][0].update({"source": "windows", "buttons": []})
        parsed = config_module.parse(raw)
        server = Server(parsed, FakePlatform())

        server._fill_dynamic_pages([("Safari", "Page"), ("OBS", "Direct")])

        self.assertEqual(len(server.config.pages[0].buttons), 2)
        self.assertEqual(config_module.to_raw(server.config)["pages"][0]["buttons"], [])

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

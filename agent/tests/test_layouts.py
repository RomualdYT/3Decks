from __future__ import annotations

import unittest


from deck3ds import config as config_module
from deck3ds.server import Server


from .fixtures import FakePlatform, minimal_config


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
        self.assertEqual([e.label for e in entries], [f"App{i}" for i in range(5)])

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

    def test_chaque_application_connue_a_une_couleur(self):
        """Deux tables séparées laissaient six applications sans couleur.

        Slack, Arc et iTerm avaient une icône mais retombaient sur le gris de
        repli. Déclarer les deux ensemble rend l'oubli impossible.
        """
        from deck3ds.server import _APP_STYLES, _icon_for

        for needle, (icon, colour) in _APP_STYLES.items():
            self.assertIn(icon, config_module.ICONS, needle)
            self.assertRegex(colour, r"^#[0-9A-F]{6}$", needle)

        for app in ("Slack", "Arc", "iTerm", "Calendrier"):
            _, colour = _icon_for(app)
            self.assertNotEqual(colour, "#64748B", f"{app} sans couleur propre")

    def test_application_inconnue_reste_neutre(self):
        from deck3ds.server import _DEFAULT_STYLE, _icon_for

        self.assertEqual(_icon_for("Logiciel inconnu"), _DEFAULT_STYLE)

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

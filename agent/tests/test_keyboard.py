from __future__ import annotations

import unittest
from pathlib import Path


from deck3ds import keys


class TestKeyCatalog(unittest.TestCase):
    """Le catalogue est l'unique source de vérité des raccourcis.

    Auparavant chaque adaptateur portait sa propre table, et les deux
    divergeaient : une touche acceptée sur un système pouvait être refusée sur
    l'autre, alors qu'un fichier de configuration est censé être portable.
    """

    def test_identifiants_uniques(self):
        noms = [key.name for key in keys.KEYS]
        self.assertEqual(len(noms), len(set(noms)), "identifiants en double")

    def test_aucun_alias_n_entre_en_collision(self):
        """Un alias qui masque un identifiant rendrait une touche inatteignable."""
        vus = {}
        for key in keys.KEYS:
            for nom in (key.name, *key.aliases):
                self.assertNotIn(
                    nom, vus, f"'{nom}' déclaré par {key.name} et {vus.get(nom)}"
                )
                vus[nom] = key.name

    def test_codes_uniques_par_plateforme(self):
        """Deux touches partageant un code en viseraient une seule en pratique."""
        for plateforme in ("mac", "win"):
            codes = [getattr(key, plateforme) for key in keys.KEYS]
            doublons = sorted({code for code in codes if codes.count(code) > 1})
            self.assertEqual(doublons, [], f"codes {plateforme} en double : {doublons}")

    def test_chaque_touche_declare_ses_deux_codes(self):
        """C'est l'invariant qui empêche les tables de diverger à nouveau.

        Déclarer les deux codes sur la même ligne rend structurellement
        impossible d'ajouter une touche pour un seul système.
        """
        for key in keys.KEYS:
            self.assertGreater(key.mac, 0, key.name)
            self.assertGreater(key.win, 0, key.name)
            self.assertTrue(key.label_en, key.name)
            self.assertTrue(key.label_fr, key.name)
            self.assertIn(key.group, keys.GROUPS, key.name)

    def test_libelles_francais_distincts_des_identifiants(self):
        """La langue ne doit plus servir de clé : elle est de l'affichage."""
        self.assertEqual(keys.BY_NAME["escape"].label_fr, "Échap")
        self.assertEqual(keys.BY_NAME["escape"].name, "escape")

    def test_modificateurs_coherents(self):
        noms = [modifier.name for modifier in keys.MODIFIERS]
        self.assertEqual(len(noms), len(set(noms)))
        for modifier in keys.MODIFIERS:
            self.assertTrue(modifier.mac.endswith("down"), modifier.name)
            self.assertGreater(modifier.win, 0, modifier.name)


class TestKeyCatalogAndEditor(unittest.TestCase):
    """L'éditeur web et l'agent doivent parler du même catalogue.

    L'interface traduit `event.code` — la position physique de la touche, donc
    indépendante de la langue du clavier — vers les identifiants de ce module.
    Une divergence produirait un raccourci proposé par l'éditeur puis refusé à
    l'enregistrement, ou l'inverse.
    """

    def _frontend_source(self, filename):

        source = Path(__file__).resolve().parent.parent / "frontend" / "src" / filename
        return source.read_text(encoding="utf-8")

    def _mapped_names(self):
        import re

        source = self._frontend_source("utils/hotkeys.ts")
        table = re.search(
            r"CODE_TO_KEY = Object\.freeze.*?\(\{(.*?)\}\);", source, re.S
        )
        self.assertIsNotNone(table, "table de correspondance introuvable")
        names = {name for _, name in re.findall(r'(\w+):\s*"([\w_]+)"', table.group(1))}
        # Les touches de fonction sont reconnues par expression régulière.
        return names | {f"f{index}" for index in range(1, 13)}

    def test_editeur_ne_cite_que_des_touches_connues(self):
        for name in self._mapped_names():
            self.assertIn(name, keys.BY_NAME, f"'{name}' absent du catalogue")

    def test_toute_touche_du_catalogue_est_capturable(self):
        """Une touche proposée mais impossible à saisir serait un piège."""
        mapped = self._mapped_names()
        missing = sorted(key.name for key in keys.KEYS if key.name not in mapped)
        self.assertEqual(missing, [], f"non capturables : {missing}")

    def test_libelles_de_groupes_traduits(self):
        """Chaque groupe exposé contient des touches bilingues utilisables."""
        catalogue = keys.catalog()
        for group in keys.GROUPS:
            entries = [item for item in catalogue["keys"] if item["group"] == group]
            self.assertTrue(entries, group)
            self.assertTrue(
                all(item["label_en"] and item["label_fr"] for item in entries)
            )


class TestParseHotkey(unittest.TestCase):
    """Analyse des combinaisons, partagée par l'éditeur et les adaptateurs.

    Une seule implémentation garantit que ce qu'accepte l'éditeur est
    exactement ce que le système saura exécuter.
    """

    def test_combinaison_simple(self):
        hotkey = keys.parse_hotkey("cmd+shift+a")
        self.assertEqual([m.name for m in hotkey.modifiers], ["cmd", "shift"])
        self.assertEqual(hotkey.character, "a")
        self.assertIsNone(hotkey.key)

    def test_touche_speciale(self):
        hotkey = keys.parse_hotkey("escape")
        self.assertEqual(hotkey.key.name, "escape")
        self.assertEqual(hotkey.character, "")

    def test_casse_ignoree(self):
        self.assertEqual(keys.parse_hotkey("ESCAPE").key.name, "escape")
        self.assertEqual(keys.parse_hotkey("Cmd+Shift+A").character, "a")

    def test_espaces_ignores(self):
        self.assertEqual(keys.parse_hotkey(" cmd + a ").canonical(), "cmd+a")

    def test_ordre_des_modificateurs_normalise(self):
        """Deux écritures équivalentes doivent produire le même enregistrement."""
        self.assertEqual(
            keys.parse_hotkey("shift+cmd+a").canonical(),
            keys.parse_hotkey("cmd+shift+a").canonical(),
        )

    def test_modificateur_repete_tolere(self):
        """`cmd+cmd+a` exprime sans ambiguïté la même intention que `cmd+a`."""
        self.assertEqual(keys.parse_hotkey("cmd+cmd+a").canonical(), "cmd+a")

    def test_alias_historiques_toujours_acceptes(self):
        """Les configurations déjà écrites ne doivent pas devenir invalides."""
        for ancien, attendu in (
            ("echap", "escape"),
            ("echappement", "escape"),
            ("esc", "escape"),
            ("entree", "return"),
            ("retour", "return"),
            ("tabulation", "tab"),
            ("espace", "space"),
            ("suppr", "forward_delete"),
            ("supprimer", "forward_delete"),
            ("gauche", "left"),
            ("droite", "right"),
            ("haut", "up"),
            ("bas", "down"),
            ("debut", "home"),
            ("fin", "end"),
            ("delete", "backspace"),
        ):
            self.assertEqual(
                keys.parse_hotkey(ancien).key.name, attendu, f"alias {ancien}"
            )

    def test_alias_de_modificateurs(self):
        for ancien, attendu in (
            ("command", "cmd"),
            ("win", "cmd"),
            ("super", "cmd"),
            ("control", "ctrl"),
            ("opt", "alt"),
            ("option", "alt"),
        ):
            hotkey = keys.parse_hotkey(f"{ancien}+a")
            self.assertEqual(hotkey.modifiers[0].name, attendu, ancien)

    def test_combinaison_vide_refusee(self):
        for texte in ("", "   ", "+", "++"):
            with self.assertRaises(keys.InvalidHotkey):
                keys.parse_hotkey(texte)

    def test_modificateur_seul_refuse(self):
        with self.assertRaises(keys.InvalidHotkey):
            keys.parse_hotkey("cmd")

    def test_deux_touches_refusees(self):
        with self.assertRaises(keys.InvalidHotkey):
            keys.parse_hotkey("a+b")

    def test_touche_inconnue_refusee(self):
        """C'est le défaut principal corrigé : refuser avant d'enregistrer."""
        for texte in ("banane", "ctrl+alt+banane", "f13"):
            with self.assertRaises(keys.InvalidHotkey) as ctx:
                keys.parse_hotkey(texte)
            self.assertIn("touche", str(ctx.exception).lower())

    def test_message_nomme_la_touche_fautive(self):
        """Un message vague obligerait l'utilisateur à deviner son erreur."""
        with self.assertRaises(keys.InvalidHotkey) as ctx:
            keys.parse_hotkey("ctrl+alt+banane")
        self.assertIn("banane", str(ctx.exception))

    def test_lettres_et_chiffres_acceptes(self):
        for texte in ("a", "z", "7", "0"):
            self.assertEqual(keys.parse_hotkey(texte).character, texte)

    def test_libelle_traduit(self):
        hotkey = keys.parse_hotkey("cmd+shift+escape")
        self.assertEqual(hotkey.label("fr"), "Cmd + Maj + Échap")
        self.assertEqual(hotkey.label("en"), "Cmd + Shift + Escape")

    def test_catalogue_expose_tout_le_necessaire(self):
        catalogue = keys.catalog("fr")
        self.assertEqual(len(catalogue["keys"]), len(keys.KEYS))
        self.assertEqual(len(catalogue["modifiers"]), len(keys.MODIFIERS))
        for entree in catalogue["keys"]:
            self.assertIn(entree["group"], catalogue["groups"])
            self.assertTrue(entree["label"])
        # Les alias ne sont jamais proposés : ils ne servent qu'à relire.
        noms = {entree["name"] for entree in catalogue["keys"]}
        self.assertNotIn("echap", noms)


# --- Adaptateur macOS ----------------------------------------------------------

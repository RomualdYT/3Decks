from __future__ import annotations

import unittest


from deck3ds.platforms.base import (
    ActionFailed,
)


from .fixtures import _mac_platform


class TestMacPathPicker(unittest.TestCase):
    """Le sélecteur natif masque les chemins techniques à l'utilisateur."""

    def test_selection_de_fichier_retourne_le_chemin(self):
        platform = _mac_platform()
        commands = []

        def run(command, timeout=0):
            commands.append((command, timeout))
            return "/Users/test/Documents/rapport.pdf\n"

        platform.run_dialog = run

        self.assertEqual(
            platform.choose_path("file"),
            "/Users/test/Documents/rapport.pdf",
        )
        self.assertIn("choose file", commands[0][0][-1])
        self.assertEqual(commands[0][1], 0)

    def test_annulation_du_selecteur_n_est_pas_une_erreur(self):
        from deck3ds.platforms.base import SelectionCancelled

        platform = _mac_platform()

        def cancel(*_args, **_kwargs):
            raise ActionFailed("User canceled. (-128)")

        platform.run_dialog = cancel

        with self.assertRaises(SelectionCancelled):
            platform.choose_path("folder")


class TestMacActionEncoding(unittest.TestCase):
    def test_nom_application_est_encode_comme_litteral_applescript(self):
        platform = _mac_platform()
        target = 'Bad" & do shell script "open /tmp/pwned" & "'

        platform.quit_app(target)

        self.assertEqual(
            platform.scripts[-1],
            'tell application "Bad\\" & do shell script '
            '\\"open /tmp/pwned\\" & \\"" to quit',
        )

    def test_caractere_de_controle_est_refuse_avant_applescript(self):
        platform = _mac_platform()

        with self.assertRaises(ActionFailed):
            platform.quit_app("Finder\nend tell")
        self.assertEqual(platform.scripts, [])

    def test_url_est_limitee_a_http_et_transmise_comme_argv(self):
        platform = _mac_platform()
        calls = []
        platform.run = lambda command, timeout=0: calls.append((command, timeout))

        platform.open_url("example.test/?a=1&b=2")
        self.assertEqual(calls, [(["open", "https://example.test/?a=1&b=2"], 8.0)])
        with self.assertRaises(ActionFailed):
            platform.open_url("file:///etc/passwd")


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
        platform = _mac_platform(
            **{
                "player state": "playing\nSuch a Shame\nTalk Talk\nIt's My Life\n\n12,5\n230",
            }
        )
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
        platform = _mac_platform(
            **{
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n30\n210000",
            }
        )
        self.assertAlmostEqual(platform.get_media().duration, 210.0)

    def test_duree_en_secondes_est_conservee(self):
        platform = _mac_platform(
            **{
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n30\n215",
            }
        )
        self.assertAlmostEqual(platform.get_media().duration, 215.0)

    def test_virgule_decimale_est_acceptee(self):
        """AppleScript suit la locale : la position peut contenir une virgule."""
        platform = _mac_platform(
            **{
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n12,5\n215",
            }
        )
        self.assertAlmostEqual(platform.get_media().position, 12.5)

    def test_lecteur_qui_refuse_l_automatisation_est_ecarte(self):
        """Un refus est temporisé, sinon chaque cycle paierait le délai."""
        from deck3ds.platforms.macos import MEDIA_PLAYERS

        platform = _mac_platform(**{"player state": ActionFailed("refus")})
        self.assertIsNone(platform.get_media())
        self.assertTrue(platform._media.retry_after)
        for player in platform._media.retry_after:
            self.assertIn(player, MEDIA_PLAYERS)

    def test_lecteur_est_reessaye_apres_une_autorisation_tardive(self):
        """Accepter la permission macOS ne doit plus imposer un redémarrage."""
        from deck3ds.platforms.macos_media import (
            FAILURE_RETRY_DELAY,
            MacMediaProvider,
        )

        now = [100.0]
        authorized = [False]
        calls = []

        def quiet(source, *args):
            calls.append(source)
            if not authorized[0]:
                return None
            return "playing\nTitre\nArtiste\nAlbum\n\n12\n180\n55"

        provider = MacMediaProvider(
            lambda source, *args: "",
            quiet,
            lambda feature: feature == "spotify",
            clock=lambda: now[0],
        )

        self.assertIsNone(provider.get_media())
        self.assertEqual(len(calls), 1)

        authorized[0] = True
        self.assertIsNone(provider.get_media())
        self.assertEqual(len(calls), 1, "la temporisation doit éviter le spam")

        now[0] += FAILURE_RETRY_DELAY
        media = provider.get_media()
        self.assertIsNotNone(media)
        self.assertEqual(media.title, "Titre")
        self.assertEqual(provider.retry_after, {})

    def test_lecteur_actif_devient_prioritaire(self):
        """Mémoriser le lecteur trouvé évite de sonder l'autre au cycle suivant."""
        platform = _mac_platform(
            **{
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2",
            }
        )
        media = platform.get_media()
        self.assertEqual(platform._media.preferred_player, media.app)

    def test_script_garde_le_test_de_presence(self):
        """Sans garde, `tell application` LANCE le lecteur au lieu de l'interroger.

        Vérifié sur macOS : un `tell` visant une application fermée la démarre.
        La collecte s'exécutant chaque seconde, sa perte ouvrirait Spotify tout
        seul. La garde doit donc précéder le `tell` dans le script.
        """
        platform = _mac_platform(
            **{
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n40",
            }
        )
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
        platform = _mac_platform(
            **{
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n40",
            }
        )
        platform.get_media()
        self.assertEqual(len(platform.scripts), 1, platform.scripts)

    def test_volume_du_lecteur_est_releve_au_passage(self):
        platform = _mac_platform(
            **{
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n40",
            }
        )
        platform.get_media()
        self.assertEqual(platform._media.volume, 40)

    def test_volume_absent_reste_indetermine(self):
        """Musique n'expose pas `sound volume` : zéro serait un mensonge."""
        platform = _mac_platform(
            **{
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n",
            }
        )
        platform.get_media()
        self.assertIsNone(platform._media.volume)

    def test_volume_du_lecteur_reste_dans_les_bornes(self):
        """La console attend un pourcentage : une valeur hors bornes la casserait."""
        platform = _mac_platform(
            **{
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n250",
            }
        )
        platform.get_media()
        self.assertEqual(platform._media.volume, 100)

    def test_volume_memorise_est_oublie_sans_lecteur(self):
        """Une valeur périmée afficherait un volume qui n'existe plus."""
        platform = _mac_platform(player_running=False)
        platform._media.volume = 40
        self.assertIsNone(platform.get_media())
        self.assertIsNone(platform._media.volume)

    def test_apple_music_extrait_la_pochette_dans_un_fichier(self):
        """Music n'expose pas d'URL : la pochette doit passer par un fichier local."""
        from deck3ds.platforms.macos_media import build_player_script

        script = build_player_script("Music")
        self.assertIn("artwork 1 of deckTrack", script)
        self.assertIn("raw data of deckArtwork", script)
        self.assertIn('"file://" & deckArtPath', script)
        self.assertIn("persistent ID of deckTrack", script)

    def test_apple_music_produit_un_media_qualifie(self):
        from deck3ds.platforms.macos_media import MacMediaProvider

        scripts = []
        provider = MacMediaProvider(
            lambda source, *args: scripts.append(source) or "",
            lambda source, *args: (
                "playing\nRunning Up That Hill\nKate Bush\nHounds of Love\n"
                "file:///tmp/3decks-music.art\n12\n298\n65"
            ),
            lambda feature: feature == "apple_music",
        )
        media = provider.get_media()
        self.assertEqual(media.app, "Apple Music")
        self.assertEqual(media.art_url, "file:///tmp/3decks-music.art")
        self.assertEqual(media.title, "Running Up That Hill")
        self.assertEqual(provider.volume, 65)

    def test_lecteur_desactive_n_est_jamais_interroge(self):
        from deck3ds.platforms.macos_media import MacMediaProvider

        calls = []
        provider = MacMediaProvider(
            lambda source, *args: calls.append(source) or "",
            lambda source, *args: calls.append(source) or "",
            lambda feature: False,
        )
        self.assertIsNone(provider.get_media())
        self.assertEqual(calls, [])


class TestMacSnapshot(unittest.TestCase):
    """Collecte groupée : c'est le chemin exécuté à chaque seconde."""

    def _snapshot(self, platform):
        platform._audio = type("A", (), {"outputs": staticmethod(lambda: [])})()
        platform._notifications = type(
            "N",
            (),
            {
                "read": staticmethod(lambda: []),
                "take_new": staticmethod(lambda entries: None),
            },
        )()
        platform._pending_notification = None
        platform.get_cpu = lambda: None
        platform.get_memory = lambda: None
        return platform.snapshot()

    def test_champs_groupes_sont_repartis(self):
        platform = _mac_platform(
            **{
                "get volume settings": "42|false|60|Safari|Safari,Dock,Finder",
            }
        )
        snapshot = self._snapshot(platform)

        self.assertEqual(snapshot.volume, 42)
        self.assertFalse(snapshot.muted)
        self.assertFalse(snapshot.mic_muted)
        self.assertEqual(snapshot.active_app, "Safari")

    def test_processus_techniques_sont_masques(self):
        """`Dock` ou `SystemUIServer` ne sont pas des applications utiles."""
        platform = _mac_platform(
            **{
                "get volume settings": "10|false|50|Safari|Safari,Dock,SystemUIServer,FolderActionsDispatcher,Notes",
            }
        )
        snapshot = self._snapshot(platform)
        self.assertEqual(snapshot.apps, ["Safari", "Notes"])

    def test_micro_a_zero_est_signale_coupe(self):
        platform = _mac_platform(
            **{
                "get volume settings": "10|false|0|Safari|Safari",
            }
        )
        self.assertTrue(self._snapshot(platform).mic_muted)

    def test_micro_illisible_retombe_sur_l_etat_suivi(self):
        """Retourner une valeur inventée afficherait un état faux sur la console."""
        platform = _mac_platform(
            **{
                "get volume settings": "10|false|inconnu|Safari|Safari",
            }
        )
        platform._mic_muted = True
        self.assertTrue(self._snapshot(platform).mic_muted)

    def test_volume_hors_bornes_est_ramene_dans_l_intervalle(self):
        platform = _mac_platform(
            **{
                "get volume settings": "250|false|50|Safari|Safari",
            }
        )
        self.assertLessEqual(self._snapshot(platform).volume, 100)

    def test_volume_du_lecteur_est_reutilise_sans_appel_supplementaire(self):
        """`get_media` a déjà relevé le volume : le redemander coûtait ~100 ms."""
        platform = _mac_platform(
            **{
                "get volume settings": "10|false|50|Spotify|Spotify",
                "player state": "playing\nTitre\nArtiste\nAlbum\n\n1\n2\n35",
            }
        )
        snapshot = self._snapshot(platform)

        self.assertEqual(snapshot.app_volume, 35)
        # Deux scripts au maximum : la collecte groupée et le lecteur.
        self.assertLessEqual(len(platform.scripts), 2, platform.scripts)

    def test_list_apps_masque_aussi_les_processus_techniques(self):
        """`list_apps` filtre la même liste que `snapshot`.

        Les deux chemins doivent produire le même résultat, sinon le repli
        afficherait des processus que la collecte groupée masque.
        """
        platform = _mac_platform(
            **{
                "background only": "Safari, Dock, SystemUIServer, Notes",
            }
        )
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

from __future__ import annotations

import inspect
import json
import unittest


from deck3ds import config as config_module
from deck3ds.actions import Dispatcher
from deck3ds.platforms.base import (
    ActionFailed,
    Platform,
)


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
            config_module.KNOWN_ACTIONS - set(config_module.ACTION_CAPABILITY) - locales
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

    def test_chaque_action_du_catalogue_a_un_handler(self):
        """Le catalogue ne doit pas annoncer une action inexécutable."""
        missing = [
            kind
            for kind in config_module.KNOWN_ACTIONS
            if not hasattr(Dispatcher, f"_do_{kind.replace('.', '_')}")
        ]
        self.assertEqual(sorted(missing), [])

    def test_windows_declare_ses_manques(self):
        """L'adaptateur Windows doit avouer ce qu'il n'implémente pas.

        Ce test échouera lorsque ces fonctions seront portées : il faudra alors
        mettre à jour la déclaration, ce qui est précisément le but.
        """
        from deck3ds.platforms.windows import WindowsPlatform

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._notifications = type("N", (), {"available": True})()
        capabilities = platform.capabilities()
        self.assertTrue(capabilities.windows)
        self.assertTrue(capabilities.audio_output)
        # Le volume par application exigerait `IAudioSessionManager2`.
        self.assertFalse(capabilities.app_volume)
        self.assertTrue(capabilities.media_artwork)
        # Ce qui fonctionne doit rester déclaré.
        self.assertTrue(capabilities.volume)
        self.assertTrue(capabilities.media)
        self.assertTrue(capabilities.notifications)

        platform._notifications.available = False
        self.assertFalse(platform.capabilities().notifications)


class TestWindowsAdapter(unittest.TestCase):
    """Comportements Windows testables sans appeler l'OS hôte."""

    def test_collecte_performance_parse_les_compteurs_groupes(self):
        from deck3ds.platforms.windows import WindowsPlatform

        class Shell:
            @staticmethod
            def run(_script, timeout=0):
                self.assertEqual(timeout, 12.0)
                return json.dumps(
                    {
                        "cpu": 31,
                        "memory": 62,
                        "memory_used_mb": 10158,
                        "memory_total_mb": 16384,
                        "disk": 74,
                        "disk_free_mb": 120000,
                        "disk_total_mb": 500000,
                        "network_down_kbps": 8500,
                        "network_up_kbps": 920,
                        "top_process": "Blender",
                        "top_process_cpu": 48,
                        "gpu": 71,
                        "temperature": None,
                    }
                )

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._shell = Shell()

        performance = platform.get_performance()

        self.assertEqual(performance.cpu, 31)
        self.assertEqual(performance.memory_total_mb, 16384)
        self.assertEqual(performance.network_down_kbps, 8500)
        self.assertEqual(performance.top_process, "Blender")
        self.assertEqual(performance.gpu, 71)
        self.assertIsNone(performance.temperature)

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
        platform._open_target = calls.append

        platform.launch_app("Safari")

        self.assertTrue(calls[0].startswith("https://"))

    def test_lancement_et_url_ne_passent_pas_par_cmd(self):
        from deck3ds.platforms.windows import WindowsPlatform

        platform = WindowsPlatform.__new__(WindowsPlatform)
        calls = []
        platform._open_target = calls.append
        platform.spawn = lambda _command: self.fail("cmd ne doit pas etre invoque")

        platform.launch_app("outil.exe & calc.exe")
        platform.open_url("example.test/?a=1&b=2")

        self.assertEqual(calls[0], "outil.exe & calc.exe")
        self.assertEqual(calls[1], "https://example.test/?a=1&b=2")

    def test_url_non_http_refusee_avant_ouverture(self):
        from deck3ds.platforms.windows import WindowsPlatform

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._open_target = lambda _target: self.fail("cible non validee")

        with self.assertRaises(ActionFailed):
            platform.open_url("javascript:alert(1)")

    def test_lettre_resolue_selon_la_disposition_du_clavier(self):
        """`ord('A')` supposait un clavier QWERTY.

        Sur un clavier AZERTY, la position que QWERTY réserve au « Q » porte
        le « A ». Convertir le caractère avec `ord` déclenchait donc une autre
        touche que celle demandée. `VkKeyScanW` interroge la disposition
        réellement installée, ce qui aligne Windows sur macOS.
        """
        import ctypes

        class User32:
            def __init__(self):
                self.events = []

            def keybd_event(self, code, _scan, flags, _extra):
                self.events.append((code, flags))

            def VkKeyScanW(self, char):
                caractere = (
                    char.value if isinstance(char, ctypes.c_wchar) else str(char)
                )
                # Disposition AZERTY : « a » est à la position du « Q ».
                return {"a": 0x51, "4": 0x34 | (1 << 8)}.get(
                    caractere, ord(caractere.upper())
                )

        from deck3ds.platforms.windows import WindowsPlatform

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._user32 = User32()
        platform.send_hotkey("ctrl+a")

        pressed = [code for code, flags in platform._user32.events if flags == 0]
        self.assertEqual(pressed, [0x11, 0x51], "le A d'AZERTY est à la place du Q")

    def test_majuscule_requise_par_la_disposition_est_ajoutee(self):
        """Sur AZERTY, « 4 » ne s'obtient qu'avec Maj.

        Sans cet ajout, la frappe produirait l'apostrophe au lieu du chiffre.
        """
        import ctypes

        class User32:
            def __init__(self):
                self.events = []

            def keybd_event(self, code, _scan, flags, _extra):
                self.events.append((code, flags))

            def VkKeyScanW(self, char):
                caractere = (
                    char.value if isinstance(char, ctypes.c_wchar) else str(char)
                )
                return {"4": 0x34 | (1 << 8)}.get(caractere, ord(caractere.upper()))

        from deck3ds.platforms.windows import WindowsPlatform

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._user32 = User32()
        platform.send_hotkey("4")

        pressed = [code for code, flags in platform._user32.events if flags == 0]
        self.assertIn(0x10, pressed, "Maj doit être ajoutée")
        self.assertIn(0x34, pressed)

    def test_touche_speciale_ignore_la_disposition(self):
        """Échap occupe la même position sur tous les claviers."""

        class User32:
            def __init__(self):
                self.events = []

            def keybd_event(self, code, _scan, flags, _extra):
                self.events.append((code, flags))

            def VkKeyScanW(self, _char):  # ne doit pas être consulté
                raise AssertionError("une touche spéciale n'a pas de caractère")

        from deck3ds.platforms.windows import WindowsPlatform

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._user32 = User32()
        platform.send_hotkey("echap")

        pressed = [code for code, flags in platform._user32.events if flags == 0]
        self.assertEqual(pressed, [0x1B])

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
            "title",
            "artist",
            "album",
            "app",
            "playing",
            "position",
            "duration",
            "key",
            "art",
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

from __future__ import annotations

import json
import time
import unittest
from pathlib import Path


from deck3ds import config as config_module


class TestWindowsNotifications(unittest.TestCase):
    """Notifications Windows via UserNotificationListener, sans base SQLite."""

    def _payload(self, *notifications, status="Allowed", error=""):
        return json.dumps(
            {
                "status": status,
                "error": error,
                "notifications": list(notifications),
            },
            ensure_ascii=False,
        )

    def _notification(
        self,
        title="Message",
        body="Bonjour",
        app="Discord",
        identifier="Discord",
        notification_id="1",
        age=5,
    ):
        return {
            "id": notification_id,
            "created": int(time.time() - age),
            "identifier": identifier,
            "app": app,
            "title": title,
            "body": body,
        }

    def _reader(self, response, request_access=True):
        from deck3ds.platforms.windows_notifications import WindowsNotificationReader

        calls = []

        def run(script, timeout):
            calls.append((script, timeout))
            return response() if callable(response) else response

        return WindowsNotificationReader(run, request_access=request_access), calls

    def test_script_utilise_uniquement_user_notification_listener(self):
        from deck3ds.platforms.windows_notifications import _script

        script = _script(True)
        self.assertIn("UserNotificationListener", script)
        self.assertIn("RequestAccessAsync", script)
        self.assertIn("GetNotificationsAsync", script)
        self.assertNotIn("wpndatabase", script.lower())
        self.assertNotIn("sqlite", script.lower())

    def test_manifeste_msix_declare_la_capacite_sans_fallback(self):
        manifest = (
            Path(__file__).resolve().parent.parent
            / "backend"
            / "windows"
            / "Package.appxmanifest.template"
        ).read_text(encoding="utf-8")

        self.assertIn('uap3:Capability Name="userNotificationListener"', manifest)
        self.assertIn('rescap:Capability Name="runFullTrust"', manifest)
        self.assertIn('ProcessorArchitecture="x64"', manifest)
        self.assertNotIn('AppListEntry="none"', manifest)
        self.assertNotIn("SQLite", manifest)
        self.assertIn("ne lit volontairement jamais wpndatabase.db", manifest)

    def test_permission_est_demandee_au_premier_demarrage(self):
        reader, calls = self._reader(self._payload())
        self.assertTrue(reader.available)
        self.assertIn("$true", calls[0][0])
        self.assertEqual(calls[0][1], 60.0)

    def test_permission_refusee_desactive_la_capacite(self):
        reader, calls = self._reader(self._payload(status="Denied"))
        self.assertFalse(reader.available)
        self.assertEqual(reader.access_status, "Denied")
        self.assertEqual(reader.read(), [])
        self.assertEqual(len(calls), 1, "aucun repli ni nouvelle invite immédiate")

    def test_avertissement_powershell_ne_masque_pas_le_json(self):
        response = "WARNING: message intermédiaire\n" + self._payload(
            self._notification()
        )
        reader, _ = self._reader(response)
        self.assertEqual(reader.read()[0].title, "Message")

    def test_notifications_triees_et_limitees(self):
        from deck3ds.platforms.macos_notifications import MAX_NOTIFICATIONS

        rows = [
            self._notification(
                title=f"T{index}",
                notification_id=str(index),
                age=MAX_NOTIFICATIONS + 4 - index,
            )
            for index in range(MAX_NOTIFICATIONS + 4)
        ]
        reader, _ = self._reader(self._payload(*rows))
        items = reader.read()

        self.assertEqual(len(items), MAX_NOTIFICATIONS)
        self.assertEqual(items[0].title, f"T{MAX_NOTIFICATIONS + 3}")

    def test_nom_winrt_et_repli_aumid(self):
        from deck3ds.platforms.windows_notifications import readable_windows_name

        self.assertEqual(
            readable_windows_name("Microsoft.WindowsStore_8wekyb3d8bbwe!App"),
            "Store",
        )
        self.assertEqual(
            readable_windows_name(r"{GUID}\Programs\Discord.lnk"),
            "Discord",
        )

        row = self._notification(
            app="",
            identifier="Windows.SystemToast.WindowsUpdate",
        )
        reader, _ = self._reader(self._payload(row))
        self.assertEqual(reader.read()[0].app, "Mise à jour")

    def test_entrees_invalides_et_trop_anciennes_ignorees(self):
        from deck3ds.platforms.macos_notifications import MAX_AGE_SECONDS

        rows = [
            {"created": "illisible", "title": "Non"},
            self._notification(title="", body="", notification_id="vide"),
            self._notification(
                title="Vieux",
                notification_id="vieux",
                age=MAX_AGE_SECONDS + 10,
            ),
            self._notification(title="Valide", notification_id="ok"),
        ]
        reader, _ = self._reader(self._payload(*rows))
        self.assertEqual([item.title for item in reader.read()], ["Valide"])

    def test_icones_valides(self):
        reader, _ = self._reader(
            self._payload(
                self._notification(app="Discord", notification_id="1"),
                self._notification(app="Inconnue", notification_id="2"),
            )
        )
        for item in reader.read():
            self.assertIn(item.icon, config_module.ICONS)

    def test_nouveaute_signalee_une_seule_fois(self):
        current = {
            "response": self._payload(
                self._notification(title="A", notification_id="1")
            )
        }
        reader, _ = self._reader(lambda: current["response"])

        first = reader.read()
        self.assertIsNone(reader.take_new(first), "pas d'annonce au démarrage")

        current["response"] = self._payload(
            self._notification(title="B", notification_id="2")
        )
        second = reader.read()
        self.assertIsNotNone(reader.take_new(second))
        self.assertIsNone(reader.take_new(second))

    def test_snapshot_windows_transmet_les_notifications(self):
        from deck3ds.platforms.macos_notifications import Notification
        from deck3ds.platforms.windows import WindowsPlatform

        item = Notification(
            app="Discord",
            title="Message",
            body="Bonjour",
            icon="chat",
            age=2,
            bundle="Discord",
            key="1",
        )

        class Reader:
            available = True

            @staticmethod
            def read():
                return [item]

            @staticmethod
            def take_new(entries):
                return entries[0]

        platform = WindowsPlatform.__new__(WindowsPlatform)
        platform._notifications = Reader()
        platform._pending_notification = None
        platform._mic_muted = False
        platform.get_volume = lambda: 30
        platform.is_muted = lambda: False
        platform.is_mic_muted = lambda: False
        platform.get_media = lambda: None
        platform.get_active_app = lambda: "Explorer"
        platform.list_apps = lambda: ["Explorer"]
        platform.get_cpu = lambda: 10
        platform.get_memory = lambda: 20
        platform.list_audio_outputs = lambda: []
        platform.get_audio_output = lambda: ""

        snapshot = platform.snapshot()

        self.assertEqual(snapshot.notifications[0].title, "Message")
        self.assertEqual(snapshot.new_notification.title, "Message")

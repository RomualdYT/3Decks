from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


from deck3ds.server import _snapshot_payload


from .fixtures import FakePlatform


class TestNotifications(unittest.TestCase):
    """Lecture et mise en forme des notifications du système."""

    def reader(self, ignored=None):
        from deck3ds.platforms.macos_notifications import NotificationReader

        return NotificationReader(ignored=ignored)

    def test_nom_lisible(self):
        from deck3ds.platforms.macos_notifications import _readable_name

        self.assertEqual(_readable_name("com.apple.mobilesms"), "Messages")
        self.assertEqual(_readable_name("com.apple.mail"), "Mail")

    def test_nom_inconnu_derive_du_paquet(self):
        from deck3ds.platforms.macos_notifications import _readable_name

        self.assertEqual(_readable_name("com.acme.superapp"), "Superapp")

    def test_prefixe_systeme_retire(self):
        from deck3ds.platforms.macos_notifications import _readable_name

        name = _readable_name("_system_center_:com.apple.followup.alert")
        self.assertNotIn("_system_center_", name)

    def test_icone_par_application(self):
        from deck3ds.config import ICONS
        from deck3ds.platforms.macos_notifications import _icon_for

        for app in ("Messages", "Musique", "Safari", "Inconnue"):
            self.assertIn(_icon_for(app), ICONS)

    def test_premiere_lecture_ne_signale_rien(self):
        """L'historique ne doit pas être annoncé au démarrage de l'agent."""
        from deck3ds.platforms.macos_notifications import Notification

        reader = self.reader()
        items = [Notification("Messages", "A", "", "chat", 10, "com.x", "k1")]
        self.assertIsNone(reader.take_new(items))

    def test_nouvelle_notification_signalee_une_fois(self):
        from deck3ds.platforms.macos_notifications import Notification

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

    def test_epoque_macos_appliquee(self):
        """Les dates de macOS partent de 2001, non de 1970.

        Sans ce décalage, toute notification paraîtrait vieille de trente ans
        et serait écartée par la limite d'ancienneté.
        """
        import time as clock

        from deck3ds.platforms.macos_notifications import _APPLE_EPOCH, _MacSource

        source = _MacSource()
        maintenant = clock.time()
        brut = maintenant - _APPLE_EPOCH

        self.assertAlmostEqual(source.timestamp(brut), maintenant, delta=1.0)
        self.assertIsNone(source.timestamp("pas un nombre"))
        self.assertIsNone(source.timestamp(True), "un booléen n'est pas une date")

    def test_base_illisible_eteint_la_lecture(self):
        """Un fichier corrompu ne doit pas être relu à chaque cycle."""
        from deck3ds.platforms.macos_notifications import NotificationReader, _MacSource

        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        corrompu = directory / "db"
        corrompu.write_bytes(b"ceci n'est pas une base SQLite")

        reader = NotificationReader(source=_MacSource(), path=corrompu)
        self.assertEqual(reader.read(), [])
        self.assertTrue(reader.broken, "la lecture doit être abandonnée")

    def test_ouverture_impossible_temporise_la_lecture(self):
        """Si `sqlite3.connect` échoue, la lecture n'insiste pas immédiatement.

        Le cas se produit lorsque le fichier existe mais reste inaccessible :
        droits refusés, chemin devenu un dossier, verrou exclusif du système.
        """
        from deck3ds.platforms import macos_notifications as notifications

        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        path = directory / "db"
        path.write_bytes(b"")

        now = [100.0]
        reader = notifications.NotificationReader(
            source=notifications._MacSource(), path=path, clock=lambda: now[0]
        )
        calls = []

        def refuser(*args, **kwargs):
            calls.append(args)
            raise sqlite3.OperationalError("acces refuse")

        with patch.object(notifications.sqlite3, "connect", refuser):
            self.assertEqual(reader.read(), [])
            self.assertEqual(reader.read(), [])

        self.assertTrue(reader.broken)
        self.assertEqual(len(calls), 1, "la temporisation doit éviter une boucle")

    def test_autorisation_tardive_est_reessayee(self):
        """Accorder l'accès complet au disque ne doit plus imposer un redémarrage."""
        from deck3ds.platforms import macos_notifications as notifications

        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        path = directory / "db"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE app (app_id INTEGER, identifier TEXT)")
        connection.execute(
            "CREATE TABLE record (app_id INTEGER, delivered_date REAL, data BLOB)"
        )
        connection.commit()
        connection.close()

        now = [100.0]
        allowed = [False]
        original_connect = sqlite3.connect
        reader = notifications.NotificationReader(
            source=notifications._MacSource(), path=path, clock=lambda: now[0]
        )

        def connect(*args, **kwargs):
            if not allowed[0]:
                raise sqlite3.OperationalError("acces refuse")
            return original_connect(*args, **kwargs)

        with patch.object(notifications.sqlite3, "connect", connect):
            self.assertFalse(reader.probe())
            allowed[0] = True
            self.assertFalse(reader.probe(), "le délai protège encore la collecte")
            now[0] += notifications.ACCESS_RETRY_DELAY
            self.assertTrue(reader.probe())

        self.assertFalse(reader.broken)

    def test_ouverture_en_lecture_seule(self):
        """La base appartient au système : l'écriture doit être impossible.

        Une ouverture en écriture créerait un journal à côté du fichier et
        pourrait le verrouiller, gênant le système lui-même.
        """
        from deck3ds.platforms.macos_notifications import NotificationReader, _MacSource

        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        path = directory / "db"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE app (app_id INTEGER, identifier TEXT)")
        connection.execute(
            "CREATE TABLE record (app_id INTEGER, delivered_date REAL, data BLOB)"
        )
        connection.commit()
        connection.close()

        reader = NotificationReader(source=_MacSource(), path=path)
        reader.read()

        # L'URI d'ouverture doit interdire l'écriture. On la reconstruit comme
        # le fait le lecteur, puis on vérifie qu'une écriture est refusée : une
        # connexion inscriptible pourrait verrouiller la base du système.
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1.0)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("INSERT INTO app VALUES (1, 'x')")
        finally:
            connection.close()

        # Aucun fichier annexe ne doit subsister à côté de la base.
        annexes = sorted(item.name for item in directory.iterdir())
        self.assertEqual(annexes, ["db"], f"fichiers créés : {annexes}")

    def test_uri_de_lecture_declaree_en_mode_ro(self):
        """Le mode est passé par URI : le vérifier fixe cette garantie.

        Sans `mode=ro`, SQLite ouvrirait la base en écriture et pourrait la
        verrouiller pendant que le système y écrit lui-même.
        """
        from deck3ds.platforms import macos_notifications as notifications

        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        path = directory / "db"
        path.write_bytes(b"")

        vues = []

        def espionner(target, *args, **kwargs):
            vues.append((target, kwargs.get("uri", False)))
            raise sqlite3.OperationalError("interrompu volontairement")

        reader = notifications.NotificationReader(
            source=notifications._MacSource(), path=path
        )
        with patch.object(notifications.sqlite3, "connect", espionner):
            reader.read()

        self.assertEqual(len(vues), 1)
        target, uri = vues[0]
        self.assertTrue(uri, "l'ouverture doit passer par une URI")
        self.assertIn("mode=ro", target)

    def test_source_choisie_selon_le_systeme(self):
        """Un système non pris en charge doit s'éteindre, pas échouer."""
        from deck3ds.platforms.macos_notifications import _MacSource, _source_for

        self.assertIsInstance(_source_for("darwin"), _MacSource)
        self.assertIsNone(
            _source_for("win32"),
            "Windows doit passer exclusivement par UserNotificationListener",
        )
        self.assertIsNone(_source_for("linux"))

    def test_systeme_non_pris_en_charge_ne_lit_rien(self):
        """Sur un système sans adaptateur, la lecture s'éteint proprement."""
        from deck3ds.platforms import macos_notifications as notifications

        with patch.object(notifications.sys, "platform", "linux"):
            reader = notifications.NotificationReader()

        self.assertIsNone(reader._source)
        self.assertIsNone(reader.path)
        self.assertFalse(reader.available)
        self.assertEqual(reader.read(), [])

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

        snapshot = FakePlatform().snapshot()
        snapshot.notifications = [
            NotificationInfo(app=f"App{i}", title=f"T{i}") for i in range(6)
        ]
        payload = _snapshot_payload(snapshot)

        # Quatre suffisent à l'affichage, le total reste indiqué.
        self.assertEqual(len(payload["notifications"]), 4)
        self.assertEqual(payload["notification_count"], 6)

    def test_snapshot_sans_notification(self):

        payload = _snapshot_payload(FakePlatform().snapshot())
        self.assertEqual(payload["notifications"], [])
        self.assertEqual(payload["notification_count"], 0)
        self.assertNotIn("notification_new", payload)

    def test_nouvelle_notification_transmise(self):
        from deck3ds.platforms.base import NotificationInfo

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
        reader.retry_after = float("inf")
        self.assertEqual(reader.read(), [])

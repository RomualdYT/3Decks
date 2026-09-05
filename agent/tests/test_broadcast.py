from __future__ import annotations

import unittest


from deck3ds import config as config_module
from deck3ds.server import Server


from .fixtures import FakePlatform, minimal_config


class TestBroadcast(unittest.IsolatedAsyncioTestCase):
    """Broadcast current state and evict clients that cannot receive it."""

    class _FakeClient:
        def __init__(self, authenticated=True, alive=True, language="en"):
            self.authenticated = authenticated
            self.alive = alive
            self.language = language
            self.sent = []
            self.raw = []
            self.closed = False

        async def send(self, message):
            if not self.alive:
                return False
            self.sent.append(message)
            return True

        async def send_raw(self, payload):
            self.raw.append(payload)
            return True

        async def close(self):
            self.closed = True

    def _server(self, *clients):
        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())
        server.log = lambda message: None
        for client in clients:
            server.clients.add(client)
        return server

    async def test_seules_les_consoles_authentifiees_recoivent(self):
        connectee = self._FakeClient(authenticated=True)
        en_attente = self._FakeClient(authenticated=False)
        server = self._server(connectee, en_attente)

        await server._broadcast({"type": "config.update"})

        self.assertEqual(len(connectee.sent), 1)
        self.assertEqual(en_attente.sent, [], "un message avant handshake fuiterait")

    async def test_console_injoignable_est_retiree(self):
        """Sans éviction, chaque cycle réécrirait dans une socket fermée."""
        morte = self._FakeClient(alive=False)
        vivante = self._FakeClient()
        server = self._server(morte, vivante)

        await server._broadcast({"type": "config.update"})

        self.assertNotIn(morte, server.clients)
        self.assertTrue(morte.closed)
        self.assertIn(vivante, server.clients)

    async def test_configuration_traduite_pour_chaque_console(self):
        raw = minimal_config()
        raw["pages"][0]["title"] = {"en": "Main", "fr": "Principal"}
        server = Server(config_module.parse(raw), FakePlatform())
        server.log = lambda message: None
        english = self._FakeClient(language="en")
        french = self._FakeClient(language="fr")
        server.clients.update((english, french))

        await server._broadcast_config()

        self.assertEqual(english.sent[0]["pages"][0]["title"], "Main")
        self.assertEqual(french.sent[0]["pages"][0]["title"], "Principal")

    async def test_pochette_transmise_apres_l_etat(self):
        client = self._FakeClient()
        server = self._server(client)

        await server._publish({"type": "state.update", "volume": 5}, b"IMG")

        self.assertEqual(len(client.sent), 1)
        self.assertEqual(client.raw, [b"IMG"])

    async def test_pochette_seule_est_transmise(self):
        """Une console qui vient d'arriver n'a aucune image, même sans delta."""
        client = self._FakeClient()
        server = self._server(client)

        await server._publish({"type": "state.update"}, b"IMG")

        self.assertEqual(client.sent, [], "aucun changement d'état à annoncer")
        self.assertEqual(client.raw, [b"IMG"])

    async def test_rien_a_dire_n_emet_rien(self):
        client = self._FakeClient()
        server = self._server(client)

        await server._publish({"type": "state.update"}, None)

        self.assertEqual(client.sent, [])
        self.assertEqual(client.raw, [])

    async def test_age_des_notifications_ne_declenche_pas_un_envoi(self):
        """La 3DS vieillit les entrées localement, sans patch JSON par seconde."""
        server = self._server()
        first = {
            "type": "state.update",
            "notifications": [
                {"app": "Mail", "title": "Message", "icon": "mail", "age": 4}
            ],
        }
        second = {
            "type": "state.update",
            "notifications": [
                {"app": "Mail", "title": "Message", "icon": "mail", "age": 5}
            ],
        }

        self.assertEqual(server._delta_since_last(first), first)
        self.assertEqual(server._delta_since_last(second), {"type": "state.update"})

    async def test_changement_de_notification_reste_transmis(self):
        server = self._server()
        server._delta_since_last(
            {
                "type": "state.update",
                "notifications": [{"title": "A", "age": 4}],
            }
        )

        delta = server._delta_since_last(
            {
                "type": "state.update",
                "notifications": [{"title": "B", "age": 5}],
            }
        )

        self.assertEqual(delta["notifications"][0]["title"], "B")


class TestArtworkRefresh(unittest.IsolatedAsyncioTestCase):
    """Pochette : jeton, teinte et transmission."""

    class _Cache:
        def __init__(self, changed, token="tok", accent="#112233"):
            self._changed = changed
            self.token = token
            self.accent = accent

        def update(self, url):
            return self._changed

        def payload(self):
            return b"IMG"

    def _server(self, cache):
        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())
        server._artwork = cache
        return server

    async def test_pochette_transmise_quand_elle_change(self):
        server = self._server(self._Cache(changed=True))
        snapshot = FakePlatform().snapshot()

        art = await server._refresh_artwork(snapshot, {"media": {}})

        self.assertEqual(art, b"IMG")

    async def test_pochette_inchangee_n_est_pas_retransmise(self):
        """La renvoyer à chaque cycle saturerait la liaison de la console."""
        server = self._server(self._Cache(changed=False))
        snapshot = FakePlatform().snapshot()

        self.assertIsNone(await server._refresh_artwork(snapshot, {"media": {}}))

    async def test_jeton_et_teinte_completent_le_media(self):
        server = self._server(self._Cache(changed=True))
        snapshot = FakePlatform().snapshot()
        payload = {"media": {"title": "T"}}

        await server._refresh_artwork(snapshot, payload)

        self.assertEqual(payload["media"]["art"], "tok")
        self.assertEqual(payload["media"]["accent"], "#112233")

    async def test_media_absent_reste_intact(self):
        server = self._server(self._Cache(changed=True))
        snapshot = FakePlatform().snapshot()
        snapshot.media = None
        payload = {"media": None}

        await server._refresh_artwork(snapshot, payload)

        self.assertIsNone(payload["media"])


class TestDynamicRepublish(unittest.IsolatedAsyncioTestCase):
    """Pages alimentées automatiquement : republier n'est pas gratuit."""

    async def _server(self):
        raw = minimal_config()
        raw["pages"][0]["source"] = "windows"
        raw["pages"][0]["layout"] = "list"
        raw["pages"][0]["buttons"] = []
        loaded = config_module.parse(raw)
        server = Server(loaded, FakePlatform())
        server.log = lambda message: None
        self.diffusions = []
        server._broadcast_config = lambda: self._note(server._config_message())
        return server

    async def _note(self, message):
        self.diffusions.append(message)

    async def test_liste_inchangee_ne_republie_pas(self):
        """Republier à chaque seconde ferait clignoter l'écran de la console."""
        server = await self._server()
        await server._republish_windows("Safari")
        premier = len(self.diffusions)

        await server._republish_windows("Safari")

        self.assertEqual(premier, 1, "la première publication est attendue")
        self.assertEqual(len(self.diffusions), 1, "la seconde est inutile")

    async def test_liste_modifiee_republie(self):
        server = await self._server()
        await server._republish_windows("Safari")
        server.platform.list_windows = lambda: [("Notes", "Autre")]

        await server._republish_windows("Notes")

        self.assertEqual(len(self.diffusions), 2)

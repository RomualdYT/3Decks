from __future__ import annotations

import unittest


from deck3ds import config as config_module
from deck3ds import protocol
from deck3ds.server import Server


from .fixtures import FakePlatform, minimal_config


class TestDirectAction(unittest.IsolatedAsyncioTestCase):
    """Actions envoyées directement par un panneau de la console.

    Elles ne figurent dans aucune page : la console transmet un nom d'action.
    C'est le seul chemin où un identifiant venu du réseau désigne du code à
    exécuter, d'où le contrôle par liste blanche.
    """

    class _FakeClient:
        id = 1
        authenticated = True

        def __init__(self):
            self.sent = []

        async def send(self, message):
            self.sent.append(message)
            return True

        async def close(self):
            pass

    def _server(self):
        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())
        server.log = lambda message: None
        return server

    async def test_action_de_la_liste_blanche_acceptee(self):
        server = self._server()
        for action in (
            "audio_output.cycle",
            "volume.mute_toggle",
            "mic.mute_toggle",
            "volume.up",
            "volume.down",
        ):
            with self.subTest(action=action):
                client = self._FakeClient()
                cible = await server._resolve_target(client, 1, "__direct", action)
                self.assertIsNotNone(cible)
                _, act = cible
                self.assertEqual(act.kind, action)

    async def test_action_connue_mais_absente_des_panneaux_est_refusee(self):
        server = self._server()
        for action in ("system.lock", "mic.unmute", "obs.record.toggle", "media.play_pause"):
            with self.subTest(action=action):
                client = self._FakeClient()
                cible = await server._resolve_target(client, 1, "__direct", action)
                self.assertIsNone(cible)
                self.assertFalse(client.sent[0]["ok"])

    async def test_action_hors_liste_blanche_refusee(self):
        """Sans ce contrôle, la console pourrait faire exécuter n'importe quoi."""
        server = self._server()
        client = self._FakeClient()

        cible = await server._resolve_target(client, 1, "__direct", "rm.tout")

        self.assertIsNone(cible, "la demande doit être rejetée")
        self.assertFalse(client.sent[0]["ok"])

    async def test_bouton_de_la_configuration_resolu(self):
        """Un bouton déclaré doit être trouvé par sa page et son identifiant."""
        server = self._server()
        client = self._FakeClient()

        cible = await server._resolve_target(client, 1, "main", "b1")

        self.assertIsNotNone(cible)
        button, action = cible
        self.assertIsNotNone(button, "le bouton de la page doit être retourné")
        self.assertIsNone(action)
        self.assertEqual(button.id, "b1")
        self.assertEqual(client.sent, [], "aucun refus ne doit être émis")

    async def test_bouton_absent_refuse(self):
        server = self._server()
        client = self._FakeClient()

        cible = await server._resolve_target(client, 1, "main", "fantome")

        self.assertIsNone(cible)
        self.assertFalse(client.sent[0]["ok"])


class TestFrameErrors(unittest.IsolatedAsyncioTestCase):
    """Une trame illisible désynchronise le flux : la connexion doit tomber."""

    class _Client:
        id = 1
        authenticated = True

        def __init__(self, error):
            self.reader_state = self._Broken(error)

        class _Broken:
            def __init__(self, error):
                self._error = error

            def __iter__(self):
                raise self._error

    async def test_trame_invalide_coupe_la_connexion(self):
        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())
        server.log = lambda message: None
        client = self._Client(protocol.ProtocolError("longueur invalide"))

        poursuivre = await server._dispatch_available(client)

        self.assertFalse(poursuivre, "rien ne permet de se resynchroniser sur le flux")


class TestClientSend(unittest.IsolatedAsyncioTestCase):
    """Distinction entre connexion perdue et message inencodable.

    Les deux cas partageaient une même clause `except` : un message trop
    volumineux faisait retirer une console dont la socket était pourtant saine,
    masquant le véritable défaut.
    """

    class _Writer:
        def __init__(self, fail=False):
            self.data = b""
            self.fail = fail

        def write(self, frame):
            self.data += frame

        async def drain(self):
            if self.fail:
                raise ConnectionResetError("connexion perdue")

    def _client(self, **kwargs):
        from deck3ds.server import Client

        client = Client.__new__(Client)
        client.id = 1
        client.writer = self._Writer(**kwargs)
        return client

    async def test_message_normal_transmis(self):
        client = self._client()
        self.assertTrue(await client.send({"type": "ping"}))
        self.assertTrue(client.writer.data)

    async def test_connexion_perdue_signalee(self):
        client = self._client(fail=True)
        self.assertFalse(await client.send({"type": "ping"}))

    async def test_message_inencodable_conserve_la_console(self):
        from deck3ds import protocol

        client = self._client()
        enorme = {"type": "state.update", "x": "a" * (protocol.MAX_MESSAGE + 1)}

        self.assertTrue(
            await client.send(enorme), "la console est jointe : elle doit rester"
        )
        self.assertEqual(client.writer.data, b"", "rien ne doit être émis")

    async def test_charge_binaire_trop_grande_conserve_la_console(self):
        from deck3ds import protocol

        client = self._client()
        self.assertTrue(await client.send_raw(b"a" * (protocol.MAX_MESSAGE + 1)))

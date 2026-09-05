from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch


from deck3ds import config as config_module
from deck3ds import protocol
from deck3ds.server import Server


from .fixtures import FakePlatform, minimal_config


class TestServerEndToEnd(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.platform = FakePlatform()
        raw = minimal_config()
        raw["pages"][0]["title"] = {"en": "Main", "fr": "Principal"}
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
        await asyncio.gather(self.poller, return_exceptions=True)
        await self.server.close()

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

    async def handshake(self, token=None, language=None, pair_code=None):
        reader, writer, frames = await self.connect()
        hello = {"type": "hello", "protocol": 1, "device": "test"}
        if token is not None:
            hello["token"] = token
        if language is not None:
            hello["language"] = language
        if pair_code is not None:
            hello["pair_code"] = pair_code
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

    async def test_handshake_localise_la_configuration(self):
        reader_en, writer_en, frames_en = await self.handshake(language="en")
        await self.receive(reader_en, frames_en, "hello.ok")
        config_en = await self.receive(reader_en, frames_en, "config.snapshot")

        reader_fr, writer_fr, frames_fr = await self.handshake(language="fr")
        await self.receive(reader_fr, frames_fr, "hello.ok")
        config_fr = await self.receive(reader_fr, frames_fr, "config.snapshot")

        self.assertEqual(config_en["pages"][0]["title"], "Main")
        self.assertEqual(config_fr["pages"][0]["title"], "Principal")

        writer_en.close()
        writer_fr.close()
        await writer_en.wait_closed()
        await writer_fr.wait_closed()

    async def test_retour_action_reste_dans_la_langue_de_chaque_console(self):
        reader_en, writer_en, frames_en = await self.handshake(language="en")
        await self.receive(reader_en, frames_en, "config.snapshot")
        reader_fr, writer_fr, frames_fr = await self.handshake(language="fr")
        await self.receive(reader_fr, frames_fr, "config.snapshot")

        writer_en.write(protocol.encode({
            "type": "button.press", "id": 1, "page": "main", "button": "vol",
        }))
        await writer_en.drain()
        result_en = await self.receive(reader_en, frames_en, "action.result")

        writer_fr.write(protocol.encode({
            "type": "button.press", "id": 2, "page": "main", "button": "vol",
        }))
        await writer_fr.drain()
        result_fr = await self.receive(reader_fr, frames_fr, "action.result")

        self.assertEqual(result_en["message"], "Volume 45%")
        self.assertEqual(result_fr["message"], "Volume 50 %")
        writer_en.close()
        writer_fr.close()
        await writer_en.wait_closed()
        await writer_fr.wait_closed()

    async def test_handshake_partiel_expire_sans_reinitialiser_le_delai(self):
        with patch("deck3ds.transports.connection.HANDSHAKE_TIMEOUT", 0.05):
            reader, writer, _frames = await self.connect()
            writer.write(protocol.encode({"type": "hello", "protocol": 1})[:2])
            await writer.drain()
            self.assertEqual(await asyncio.wait_for(reader.read(1), 0.5), b"")
        writer.close()
        await writer.wait_closed()

    async def test_connexions_en_attente_sont_bornees(self):
        with patch("deck3ds.transports.connection.MAX_PENDING_CONNECTIONS", 1):
            reader1, writer1, _frames1 = await self.connect()
            reader2, writer2, frames2 = await self.connect()
            error = await self.receive(reader2, frames2, "hello.error")
            self.assertEqual(error["code"], "server_busy")
        writer1.close()
        writer2.close()
        await writer1.wait_closed()
        await writer2.wait_closed()

    async def test_consoles_authentifiees_sont_bornees(self):
        reader1, writer1, frames1 = await self.handshake()
        await self.receive(reader1, frames1, "hello.ok")
        with patch("deck3ds.transports.handshake.MAX_AUTHENTICATED_CLIENTS", 1):
            reader2, writer2, frames2 = await self.handshake()
            error = await self.receive(reader2, frames2, "hello.error")
            self.assertEqual(error["code"], "server_busy")
        writer1.close()
        writer2.close()
        await writer1.wait_closed()
        await writer2.wait_closed()

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

    async def test_second_handshake_ferme_sans_traiter_la_trame_suivante(self):
        reader, writer, frames = await self.handshake()
        await self.receive(reader, frames, "hello.ok")
        writer.write(
            protocol.encode({"type": "hello", "protocol": 1})
            + protocol.encode(
                {"type": "button.press", "id": 9, "page": "main", "button": "mic"}
            )
        )
        await writer.drain()

        error = await self.receive(reader, frames, "hello.error")
        self.assertIn("deja", error["reason"])
        await asyncio.sleep(0)
        self.assertFalse(self.platform.mic_muted)
        writer.close()
        await writer.wait_closed()

    async def test_jeton_invalide_refuse(self):
        self.server.config.token = "bonjeton"

        reader, writer, frames = await self.handshake(token="mauvais")
        error = await self.receive(reader, frames, "hello.error")
        self.assertIn("jeton", error["reason"])

        writer.close()
        await writer.wait_closed()

    async def test_jeton_valide_accepte(self):
        self.server.config.token = "bonjeton"

        reader, writer, frames = await self.handshake(token="bonjeton")
        await self.receive(reader, frames, "hello.ok")

        writer.close()
        await writer.wait_closed()

    async def test_code_court_appaire_et_renvoie_le_jeton(self):
        self.server.config.token = "jeton-durable"
        code = self.server.pairing.snapshot(required=True)["code"]

        reader, writer, frames = await self.handshake(pair_code=code)
        ok = await self.receive(reader, frames, "hello.ok")
        credential = ok["token"]
        self.assertRegex(credential, r"^d3d_[0-9a-f]{16}\.[A-Za-z0-9_-]{32}$")
        self.assertNotEqual(credential, "jeton-durable")
        writer.close()
        await writer.wait_closed()

        # Le secret individuel est accepté sans réutiliser le jeton maître et
        # n'est pas renvoyé une seconde fois.
        reader_known, writer_known, frames_known = await self.handshake(token=credential)
        known = await self.receive(reader_known, frames_known, "hello.ok")
        self.assertNotIn("token", known)
        writer_known.close()
        await writer_known.wait_closed()

        # Un code consommé ne peut pas autoriser une seconde console.
        reader2, writer2, frames2 = await self.handshake(pair_code=code)
        error = await self.receive(reader2, frames2, "hello.error")
        self.assertEqual(error["code"], "pairing_required")
        writer2.close()
        await writer2.wait_closed()

    async def test_action_dupliquee_est_refusee_sans_second_effet(self):
        reader, writer, frames = await self.handshake()
        await self.receive(reader, frames, "config.snapshot")
        press = protocol.encode(
            {"type": "button.press", "id": 7, "page": "main", "button": "mic"}
        )
        writer.write(press + press)
        await writer.drain()

        first = await self.receive(reader, frames, "action.result")
        second = await self.receive(reader, frames, "action.result")
        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertIn("deja", second["message"])
        self.assertTrue(self.platform.mic_muted)
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

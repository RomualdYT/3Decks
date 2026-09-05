from __future__ import annotations

import unittest
from pathlib import Path


from deck3ds import protocol
from deck3ds.platforms.base import (
    MediaInfo,
)
from deck3ds.server import _snapshot_payload


from .fixtures import FakePlatform


class TestProtocol(unittest.TestCase):
    def test_aller_retour(self):
        original = {"type": "ping", "id": 3}
        raw = protocol.encode(original)

        reader = protocol.FrameReader()
        reader.feed(raw)
        self.assertEqual(list(reader), [original])

    def test_entete_longueur(self):
        raw = protocol.encode({"type": "ping", "id": 1})
        payload_length = int.from_bytes(raw[:4], "big")
        self.assertEqual(payload_length, len(raw) - 4)

    def test_messages_colles(self):
        """TCP peut livrer plusieurs messages d'un coup."""
        data = protocol.encode({"type": "ping", "id": 1}) + protocol.encode(
            {"type": "ping", "id": 2}
        )
        reader = protocol.FrameReader()
        reader.feed(data)
        self.assertEqual([m["id"] for m in reader], [1, 2])

    def test_message_fragmente(self):
        """TCP peut aussi livrer un message en plusieurs morceaux."""
        data = protocol.encode({"type": "ping", "id": 7})
        reader = protocol.FrameReader()

        for index in range(len(data) - 1):
            reader.feed(data[index : index + 1])
            self.assertEqual(list(reader), [], "message incomplet livre trop tot")

        reader.feed(data[-1:])
        self.assertEqual([m["id"] for m in reader], [7])

    def test_fragmentation_octet_par_octet_multiple(self):
        data = protocol.encode({"type": "ping", "id": 1}) + protocol.encode(
            {"type": "pong", "id": 2}
        )
        reader = protocol.FrameReader()
        received = []
        for byte in data:
            reader.feed(bytes([byte]))
            received.extend(reader)
        self.assertEqual([m["id"] for m in received], [1, 2])

    def test_longueur_aberrante_rejetee(self):
        reader = protocol.FrameReader()
        reader.feed((10**9).to_bytes(4, "big") + b"x")
        with self.assertRaises(protocol.ProtocolError):
            list(reader)

    def test_json_invalide_rejete(self):
        payload = b"{pas du json"
        reader = protocol.FrameReader()
        reader.feed(len(payload).to_bytes(4, "big") + payload)
        with self.assertRaises(protocol.ProtocolError):
            list(reader)

    def test_racine_non_objet_rejetee(self):
        payload = b"[1,2,3]"
        reader = protocol.FrameReader()
        reader.feed(len(payload).to_bytes(4, "big") + payload)
        with self.assertRaises(protocol.ProtocolError):
            list(reader)

    def test_utf8_preserve(self):
        message = {"type": "action.result", "message": "Micro coupé — été"}
        reader = protocol.FrameReader()
        reader.feed(protocol.encode(message))
        self.assertEqual(list(reader)[0]["message"], "Micro coupé — été")

    def test_message_trop_grand_refuse(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.encode({"type": "x", "data": "a" * (protocol.MAX_MESSAGE + 10)})


# --- Configuration ------------------------------------------------------------


class TestMessages(unittest.TestCase):
    """Traduction des notifications renvoyées à la console."""

    def tearDown(self):
        from deck3ds import messages

        messages.set_language("en")

    def _sources(self):

        from deck3ds import actions

        root = Path(actions.__file__).parent
        return "".join(
            (root / name).read_text(encoding="utf-8")
            for name in (
                "actions.py",
                "server.py",
                "obs.py",
                "platforms/base.py",
                "platforms/macos.py",
                "platforms/windows.py",
            )
        )

    def test_aucune_traduction_inutilisee(self):
        """Une clé jamais appelée signale un message écrit en dur ailleurs.

        Quatre clés traduites étaient ignorées, les adaptateurs levant des
        libellés français littéraux : la console recevait donc du français
        même lorsqu'elle demandait l'anglais.
        """
        import re

        from deck3ds import messages

        used = set(re.findall(r'msg\(\s*"(\w+)"', self._sources()))
        unused = sorted(set(messages._CATALOGUE["en"]) - used)
        self.assertEqual(unused, [], f"traductions inutilisées : {unused}")

    def test_aucun_message_utilisateur_en_dur(self):
        """Les libellés destinés à la console doivent passer par `msg`."""
        import re

        sources = self._sources()
        # Ces tournures indiquent un message rédigé pour l'utilisateur.
        for pattern in (
            r'ActionFailed\(\s*"[^"]*sortie[^"]*"',
            r'ActionFailed\(\s*f?"[^"]*introuvable[^"]*"',
            r'ActionFailed\(\s*"[^"]*invalide[^"]*"',
        ):
            self.assertIsNone(
                re.search(pattern, sources),
                f"message en dur détecté : {pattern}",
            )

    def test_anglais_par_defaut(self):
        from deck3ds import messages

        messages.set_language("en")
        self.assertEqual(messages.msg("mic_muted"), "Mic muted")

    def test_francais(self):
        from deck3ds import messages

        messages.set_language("fr")
        self.assertEqual(messages.msg("mic_muted"), "Micro coupé")

    def test_langue_inconnue_retombe_en_anglais(self):
        from deck3ds import messages

        messages.set_language("de")
        self.assertEqual(messages.language(), "en")

    def test_substitution(self):
        from deck3ds import messages

        messages.set_language("en")
        self.assertIn("42", messages.msg("volume_set", value=42))

    def test_cle_absente_ne_leve_pas(self):
        from deck3ds import messages

        self.assertEqual(messages.msg("cle_inexistante"), "cle_inexistante")

    def test_valeur_manquante_ne_leve_pas(self):
        from deck3ds import messages

        # Le gabarit attend `value` : son absence ne doit pas provoquer d'erreur.
        self.assertTrue(messages.msg("volume_set"))

    def test_toutes_les_cles_traduites(self):
        """Chaque clé anglaise doit avoir son équivalent français."""
        from deck3ds.messages import _CATALOGUE

        manquantes = set(_CATALOGUE["en"]) - set(_CATALOGUE["fr"])
        self.assertEqual(manquantes, set(), f"clés sans traduction : {manquantes}")


class TestPairingRateLimit(unittest.TestCase):
    def test_cinq_echecs_bloquent_temporairement_la_source(self):
        from deck3ds.pairing import PairingManager

        now = [100.0]
        pairing = PairingManager(clock=lambda: now[0])
        code = pairing.snapshot(required=True)["code"]
        wrong = "000000" if code != "000000" else "000001"
        for _attempt in range(5):
            self.assertFalse(pairing.consume(wrong, "192.0.2.10"))
        self.assertFalse(pairing.consume(code, "192.0.2.10"))

        now[0] += 61
        self.assertTrue(pairing.consume(code, "192.0.2.10"))

    def test_quota_est_isole_par_adresse_et_rotation_le_reinitialise(self):
        from deck3ds.pairing import PairingManager

        pairing = PairingManager(clock=lambda: 100.0)
        code = pairing.snapshot(required=True)["code"]
        wrong = "000000" if code != "000000" else "000001"
        for _attempt in range(5):
            pairing.consume(wrong, "192.0.2.10")
        self.assertTrue(pairing.consume(code, "192.0.2.11"))

        current = pairing.snapshot(required=True)["code"]
        wrong = "000000" if current != "000000" else "000001"
        for _attempt in range(5):
            pairing.consume(wrong, "192.0.2.10")
        fresh = pairing.rotate()
        self.assertTrue(pairing.consume(fresh, "192.0.2.10"))

    def test_code_exige_exactement_six_chiffres_ascii(self):
        from deck3ds.pairing import PairingManager

        pairing = PairingManager()
        code = pairing.snapshot(required=True)["code"]
        self.assertFalse(pairing.consume(f" {code}", "test"))
        self.assertFalse(pairing.consume(code + "0", "test"))

    def test_quota_global_borne_les_sources_multiples(self):
        from unittest.mock import patch

        from deck3ds.pairing import PairingManager

        pairing = PairingManager(clock=lambda: 100.0)
        code = pairing.snapshot(required=True)["code"]
        wrong = "000000" if code != "000000" else "000001"
        with patch("deck3ds.pairing.PAIRING_ATTEMPTS_GLOBAL", 3):
            for attempt in range(3):
                self.assertFalse(pairing.consume(wrong, f"192.0.2.{attempt}"))
            self.assertFalse(pairing.consume(code, "198.51.100.1"))


# --- Catalogue de touches ------------------------------------------------------


class TestStatePayload(unittest.TestCase):
    def test_valeurs_inconnues_omises(self):
        snapshot = FakePlatform().snapshot()
        snapshot.volume = None
        snapshot.cpu = None
        payload = _snapshot_payload(snapshot)
        self.assertNotIn("volume", payload)
        self.assertNotIn("cpu", payload)
        self.assertIn("time", payload)

    def test_media_absent_devient_null(self):
        snapshot = FakePlatform().snapshot()
        snapshot.media = None
        self.assertIsNone(_snapshot_payload(snapshot)["media"])

    def test_media_sans_titre_devient_null(self):
        snapshot = FakePlatform().snapshot()
        snapshot.media = MediaInfo("", "", "", False)
        self.assertIsNone(_snapshot_payload(snapshot)["media"])

    def test_liste_apps_bornee(self):
        snapshot = FakePlatform().snapshot()
        snapshot.apps = [f"App{i}" for i in range(30)]
        self.assertLessEqual(len(_snapshot_payload(snapshot)["apps"]), 8)

    def test_payload_encodable(self):
        payload = _snapshot_payload(FakePlatform().snapshot())
        self.assertTrue(protocol.encode(payload))

    def test_mesures_de_performance_facultatives_sont_transmises(self):
        snapshot = FakePlatform().snapshot()
        snapshot.memory_used_mb = 8192
        snapshot.memory_total_mb = 16384
        snapshot.disk = 72
        snapshot.network_down_kbps = 12500
        snapshot.top_process = "Blender"
        snapshot.top_process_cpu = 44

        payload = _snapshot_payload(snapshot)

        self.assertEqual(payload["memory_total_mb"], 16384)
        self.assertEqual(payload["network_down_kbps"], 12500)
        self.assertEqual(payload["top_process"], "Blender")
        self.assertEqual(payload["top_process_cpu"], 44)


# --- Serveur, de bout en bout --------------------------------------------------

from __future__ import annotations

import json
import unittest


class TestDiscovery(unittest.TestCase):
    class Owner:
        def __init__(self):
            self.debugged = []

        def discovery_payload(self):
            return {
                "type": "deck3ds.agent",
                "protocol": 1,
                "name": "Mac de test",
                "platform": "macos",
                "port": 38123,
                "pairing_required": True,
            }

        def debug(self, message):
            self.debugged.append(message)

        def log(self, message):
            self.debugged.append(message)

    class Transport:
        def __init__(self):
            self.sent = []

        def sendto(self, payload, address):
            self.sent.append((payload, address))

    def test_annonce_repond_a_une_console_compatible(self):
        from deck3ds.transports.discovery import _DiscoveryProtocol

        owner = self.Owner()
        transport = self.Transport()
        discovery = _DiscoveryProtocol(owner)
        discovery.connection_made(transport)
        discovery.datagram_received(
            json.dumps(
                {"type": "deck3ds.discover", "protocol": 1, "nonce": 42}
            ).encode(),
            ("192.168.1.50", 50000),
        )

        self.assertEqual(len(transport.sent), 1)
        payload = json.loads(transport.sent[0][0])
        self.assertEqual(payload["name"], "Mac de test")
        self.assertEqual(payload["nonce"], 42)
        self.assertTrue(payload["pairing_required"])

    def test_annonce_ignore_un_protocole_incompatible(self):
        from deck3ds.transports.discovery import _DiscoveryProtocol

        transport = self.Transport()
        discovery = _DiscoveryProtocol(self.Owner())
        discovery.connection_made(transport)
        discovery.datagram_received(
            b'{"type":"deck3ds.discover","protocol":999}',
            ("192.168.1.50", 50000),
        )
        self.assertEqual(transport.sent, [])

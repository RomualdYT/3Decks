"""Exécution des commandes reçues d'une console."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from .. import protocol
from .. import config as config_module
from ..config import Action
from .parts import Client


class CommandMixin:
    async def _resolve_target(
        self, client: Client, request_id: int, page_id: str, button_id: str
    ):
        """Retrouve ce qu'un appui désigne, ou refuse la demande.

        Trois provenances sont possibles : un bouton de la configuration, un
        élément de liste — qui emprunte le même message que la grille — ou un
        panneau de la console, qui envoie directement un nom d'action.

        Retourne `(bouton, action)` dont au plus un est renseigné, ou `None` si
        la demande a été refusée et la réponse déjà émise.
        """
        if page_id == "__direct":
            # La console transmet le nom de l'action. Seules celles de la liste
            # blanche sont acceptées, comme partout ailleurs.
            if button_id not in config_module.KNOWN_ACTIONS:
                await client.send(
                    protocol.action_result(request_id, False, "action inconnue")
                )
                self.log(f"Console #{client.id}: action refusee {button_id}")
                return None
            return None, Action(button_id, {})

        button = self.config.find_button(page_id, button_id)
        if button is not None:
            return button, None

        action = self.config.find_action(page_id, button_id)
        if action is None:
            await client.send(
                protocol.action_result(request_id, False, "bouton inconnu")
            )
            self.log(f"Console #{client.id}: element inconnu {page_id}/{button_id}")
            return None
        return None, action
    async def _run_action(self, button, action, hold: bool):
        """Exécute l'action demandée et mesure sa durée.

        L'exécution peut appeler AppleScript ou PowerShell : elle est déportée
        dans un fil pour que la boucle d'événements reste réactive.
        """
        started = time.monotonic()
        if button is not None:
            outcome = await asyncio.to_thread(
                self.dispatcher.run_button, button, hold
            )
        else:
            outcome = await asyncio.to_thread(self.dispatcher.run, action)
        return outcome, (time.monotonic() - started) * 1000.0
    def _schedule_confirmation(self, outcome) -> None:
        """Provoque une collecte immédiate lorsque l'action a modifié le poste.

        Sans elle, l'écran conserverait l'ancien état jusqu'au cycle suivant et
        le bouton semblerait sans effet.
        """
        if not outcome.state_changed:
            return
        if outcome.slow_effect:
            self._slow_confirm = True
        self._wake().set()
    async def _handle_button(self, client: Client, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        if not isinstance(request_id, int):
            request_id = 0

        page_id = message.get("page")
        button_id = message.get("button")
        hold = bool(message.get("hold", False))

        if not isinstance(page_id, str) or not isinstance(button_id, str):
            await client.send(
                protocol.action_result(request_id, False, "requete invalide")
            )
            return

        target = await self._resolve_target(client, request_id, page_id, button_id)
        if target is None:
            return

        button, action = target
        outcome, elapsed = await self._run_action(button, action, hold)

        status = "ok" if outcome.ok else "echec"
        self.log(
            f"Console #{client.id}: {page_id}/{button_id}"
            f"{' (long)' if hold else ''} -> {status}"
            f" [{elapsed:.0f} ms]"
            + (f" {outcome.message}" if outcome.message else "")
        )

        await client.send(
            protocol.action_result(
                request_id,
                outcome.ok,
                outcome.message,
                outcome.open_page,
                outcome.open_settings,
                outcome.open_modal,
                outcome.toggle_frame,
            )
        )
        self._schedule_confirmation(outcome)
    async def _handle_value(self, client: Client, message: dict[str, Any]) -> None:
        """Applique un réglage continu venu d'un curseur.

        Les curseurs transmettent la valeur voulue plutôt qu'une succession
        d'incréments : un seul message suffit là où les boutons plus et moins en
        demandaient une dizaine.
        """
        request_id = message.get("id")
        if not isinstance(request_id, int):
            request_id = 0

        target = message.get("target")
        value = message.get("value")

        if not isinstance(target, str) or not isinstance(value, int):
            await client.send(
                protocol.action_result(request_id, False, "requete invalide")
            )
            return

        # Seuls les réglages continus connus sont acceptés : la console ne peut
        # pas désigner une propriété arbitraire.
        allowed = {"volume": "volume.set", "app_volume": "app_volume.set"}
        kind = allowed.get(target)

        if kind is None:
            await client.send(
                protocol.action_result(request_id, False, "reglage inconnu")
            )
            return

        outcome = await asyncio.to_thread(
            self.dispatcher.run, Action(kind, {"value": value})
        )

        await client.send(
            protocol.action_result(request_id, outcome.ok, outcome.message)
        )

        if outcome.state_changed:
            self._wake().set()

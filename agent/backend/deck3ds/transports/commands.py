"""Exécution des commandes reçues d'une console."""

from __future__ import annotations

import time
from typing import Any
from .. import protocol
from ..config import Action, ButtonConfig
from ..actions import ActionOutcome
from .parts import Client


from .ports import AgentPort


# Seuls les contrôles codés en dur dans les panneaux système de la 3DS peuvent
# contourner une page configurée. Étendre le catalogue des actions ne doit
# jamais étendre implicitement cette frontière réseau.
DIRECT_ACTIONS = frozenset(
    {"audio_output.cycle", "volume.mute_toggle", "mic.mute_toggle"}
)


class Command:
    def __init__(self, context: AgentPort) -> None:
        self.context = context

    async def _accept_action_request(
        self, client: Client, message: dict[str, Any]
    ) -> int | None:
        """Reject duplicate/out-of-order mutations within one TCP session."""
        request_id = message.get("id")
        if type(request_id) is not int or request_id < 0:
            await client.send(protocol.action_result(0, False, "requete invalide"))
            return None
        if request_id <= client.last_action_id:
            await client.send(
                protocol.action_result(request_id, False, "requete deja traitee")
            )
            self.context.event(
                "action.replay_rejected",
                f"Console #{client.id}: requete rejouee refusee",
                level="warning",
                client_id=client.id,
                request_id=request_id,
            )
            return None
        client.last_action_id = request_id
        return request_id

    async def _reject_if_paused(self, client: Client, request_id: int) -> bool:
        if not self.context.controls_paused:
            return False
        message = (
            "Agent en pause — reprenez-le depuis la barre des menus."
            if client.language == "fr"
            else "Agent paused — resume it from the system menu."
        )
        await client.send(protocol.action_result(request_id, False, message))
        self.context.event(
            "action.paused",
            f"Console #{client.id}: commande refusee pendant la pause",
            level="info",
            client_id=client.id,
            request_id=request_id,
        )
        return True

    async def _resolve_target(
        self, client: Client, request_id: int, page_id: str, button_id: str
    ) -> tuple[ButtonConfig | None, Action | None] | None:
        """Retrouve ce qu'un appui désigne, ou refuse la demande.

        Trois provenances sont possibles : un bouton de la configuration, un
        élément de liste — qui emprunte le même message que la grille — ou un
        panneau de la console, qui envoie directement un nom d'action.

        Retourne `(bouton, action)` dont au plus un est renseigné, ou `None` si
        la demande a été refusée et la réponse déjà émise.
        """
        if page_id == "__direct":
            if button_id not in DIRECT_ACTIONS:
                await client.send(
                    protocol.action_result(request_id, False, "action inconnue")
                )
                self.context.event(
                    "action.denied",
                    f"Console #{client.id}: action refusee {button_id}",
                    level="warning",
                    client_id=client.id,
                    action=button_id,
                )
                return None
            return None, Action(button_id, {})

        button = self.context.config.find_button(page_id, button_id)
        if button is not None:
            return button, None

        action = self.context.config.find_action(page_id, button_id)
        if action is None:
            await client.send(
                protocol.action_result(request_id, False, "bouton inconnu")
            )
            self.context.event(
                "action.unknown",
                f"Console #{client.id}: element inconnu {page_id}/{button_id}",
                level="warning",
                client_id=client.id,
                page=page_id,
                button=button_id,
            )
            return None
        return None, action

    async def _run_action(
        self,
        button: ButtonConfig | None,
        action: Action | None,
        hold: bool,
        language: str,
    ) -> tuple[ActionOutcome, float]:
        """Exécute l'action demandée et mesure sa durée.

        L'exécution peut appeler AppleScript ou PowerShell : elle est déportée
        dans un fil pour que la boucle d'événements reste réactive.
        """
        started = time.monotonic()
        selected = (
            (button.hold_action if hold and button.hold_action else button.action)
            if button
            else action
        )
        pool = (
            self.context.extension_actions_pool
            if selected and selected.kind.startswith("ext:")
            else self.context.actions_pool
        )
        if button is not None:
            outcome = await pool.run(
                self.context.dispatcher.run_button, button, hold, language
            )
        else:
            assert action is not None
            outcome = await pool.run(self.context.dispatcher.run, action, language)
        return outcome, (time.monotonic() - started) * 1000.0

    def _schedule_confirmation(self, outcome: ActionOutcome) -> None:
        """Provoque une collecte immédiate lorsque l'action a modifié le poste.

        Sans elle, l'écran conserverait l'ancien état jusqu'au cycle suivant et
        le bouton semblerait sans effet.
        """
        if not outcome.state_changed:
            return
        if outcome.slow_effect:
            self.context._slow_confirm = True
        self.context._wake().set()

    async def _handle_button(self, client: Client, message: dict[str, Any]) -> None:
        request_id = await self._accept_action_request(client, message)
        if request_id is None:
            return
        if await self._reject_if_paused(client, request_id):
            return

        page_id = message.get("page")
        button_id = message.get("button")
        hold = bool(message.get("hold", False))

        if not isinstance(page_id, str) or not isinstance(button_id, str):
            await client.send(
                protocol.action_result(request_id, False, "requete invalide")
            )
            return

        target = await self.context._resolve_target(
            client, request_id, page_id, button_id
        )
        if target is None:
            return

        button, action = target
        outcome, elapsed = await self.context._run_action(
            button, action, hold, client.language
        )

        status = "ok" if outcome.ok else "echec"
        self.context.event(
            "action.succeeded" if outcome.ok else "action.failed",
            f"Console #{client.id}: {page_id}/{button_id}"
            f"{' (long)' if hold else ''} -> {status}"
            f" [{elapsed:.0f} ms]" + (f" {outcome.message}" if outcome.message else ""),
            level="info" if outcome.ok else "warning",
            client_id=client.id,
            page=page_id,
            button=button_id,
            hold=hold,
            elapsed_ms=round(elapsed, 1),
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
        self.context._schedule_confirmation(outcome)

    async def _handle_value(self, client: Client, message: dict[str, Any]) -> None:
        """Applique un réglage continu venu d'un curseur.

        Les curseurs transmettent la valeur voulue plutôt qu'une succession
        d'incréments : un seul message suffit là où les boutons plus et moins en
        demandaient une dizaine.
        """
        request_id = await self._accept_action_request(client, message)
        if request_id is None:
            return
        if await self._reject_if_paused(client, request_id):
            return

        target = message.get("target")
        value = message.get("value")

        if (
            not isinstance(target, str)
            or type(value) is not int
            or not 0 <= value <= 100
        ):
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

        outcome = await self.context.actions_pool.run(
            self.context.dispatcher.run,
            Action(kind, {"value": value}),
            client.language,
        )

        self.context.event(
            "action.succeeded" if outcome.ok else "action.failed",
            client_id=client.id,
            action=kind,
            target=target,
            value=value,
        )

        await client.send(
            protocol.action_result(request_id, outcome.ok, outcome.message)
        )

        if outcome.state_changed:
            self.context._wake().set()

"""Collecte périodique de l'état du poste et diffusion du différentiel."""

from __future__ import annotations

import asyncio
from typing import Any
from ..platforms.base import SystemSnapshot
from .parts import SETTLE_DELAY, SLOW_CONFIRM_DELAY, _snapshot_payload


class CollectMixin:
    def _wake(self) -> asyncio.Event:
        """Signal de rafraîchissement, créé à la première utilisation.

        Voir le commentaire du constructeur : la création doit avoir lieu dans
        la boucle qui l'attend.
        """
        if self._refresh_event is None:
            self._refresh_event = asyncio.Event()
        return self._refresh_event
    async def _wait_for_wake(self) -> bool:
        """Attend un réveil ou l'expiration de l'intervalle de collecte.

        Retourne `True` si une action a demandé un rafraîchissement immédiat.
        """
        try:
            await asyncio.wait_for(
                self._wake().wait(), timeout=self.config.poll_interval
            )
        except asyncio.TimeoutError:
            return False
        self._wake().clear()
        return True
    async def _collect_safely(self) -> None:
        """Collecte l'état sans jamais laisser une panne arrêter la boucle."""
        try:
            await self._refresh_state()
        except Exception as error:  # la boucle ne doit jamais s'arrêter
            self.debug(f"collecte en echec: {type(error).__name__}: {error}")
    async def _confirm_after_action(self) -> None:
        """Relit l'état après une action, une fois le système stabilisé.

        Une lecture immédiate rapporterait encore l'ancienne valeur. Certaines
        commandes demandent bien davantage : une diffusion Spotify vers une
        enceinte externe met environ deux secondes à changer l'état de lecture,
        d'où la seconde relecture différée.

        Ces relectures ne sont pas protégées, contrairement à la collecte
        périodique : une panne survenant ici doit remonter jusqu'à `_poll_loop`,
        qui la journalise. La masquer priverait du diagnostic.
        """
        await asyncio.sleep(SETTLE_DELAY)
        await self._refresh_state()

        if not self._slow_confirm:
            return
        self._slow_confirm = False
        await asyncio.sleep(SLOW_CONFIRM_DELAY)
        await self._refresh_state()
    async def _poll_forever(self) -> None:
        while True:
            # Le fichier de configuration est relu si nécessaire avant chaque
            # collecte : une modification est ainsi appliquée en quelques
            # secondes, sans redémarrer l'agent.
            if self.reload_config_if_changed():
                await self._broadcast(self._config_message())

            await self._collect_safely()

            if await self._wait_for_wake():
                await self._confirm_after_action()
    async def _refresh_state(self) -> None:
        """Collecte l'état du poste et diffuse ce qui a changé.

        Chaque étape est isolée : la collecte, la remise à jour des pages
        dynamiques, la pochette, puis la diffusion du différentiel.
        """
        if not self.clients:
            # Personne n'écoute : inutile de solliciter le système.
            return

        snapshot = await asyncio.to_thread(self.platform.snapshot)
        payload = _snapshot_payload(snapshot)

        await self._republish_windows(snapshot.active_app)
        art = await self._refresh_artwork(snapshot, payload)
        await self._publish(self._delta_since_last(payload), art)
    async def _republish_windows(self, active_app: str) -> None:
        """Reconstruit les pages alimentées automatiquement, si nécessaire.

        La configuration n'est renvoyée que lorsque la liste des fenêtres a
        réellement changé : sinon la console rebâtirait son interface à chaque
        seconde.
        """
        if not self._has_dynamic_pages():
            return

        windows = await asyncio.to_thread(self.platform.list_windows)
        if windows == self._published_windows:
            return

        self._fill_dynamic_pages(windows, active_app)
        await self._broadcast(self._config_message())
    async def _refresh_artwork(
        self, snapshot: SystemSnapshot, payload: dict[str, Any]
    ) -> bytes | None:
        """Prépare la pochette et complète le message d'état.

        Téléchargement et conversion se font dans un fil : ils ne doivent pas
        retarder la boucle d'événements. Le jeton permet à la console d'ignorer
        une image qu'elle possède déjà.

        Retourne la charge binaire à transmettre, ou `None` si rien n'a changé.
        """
        art_url = snapshot.media.art_url if snapshot.media is not None else ""
        changed = await asyncio.to_thread(self._artwork.update, art_url)

        media = payload.get("media")
        if isinstance(media, dict) and self._artwork.token:
            media["art"] = self._artwork.token
            if self._artwork.accent:
                media["accent"] = self._artwork.accent

        return self._artwork.payload() if changed else None
    def _delta_since_last(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Champs modifiés depuis la dernière diffusion.

        N'émettre que les différences limite le trafic et le travail de la
        console. Le type est toujours conservé : il identifie le message.
        """
        previous = self._last_payload
        self._last_payload = payload

        if previous is None:
            return payload

        delta: dict[str, Any] = {}
        for key, value in payload.items():
            if key == "type":
                delta[key] = value
                continue

            previous_value = previous.get(key)
            if key == "notifications" and isinstance(value, list):
                # L'âge évolue toutes les secondes alors que le contenu reste
                # identique. La 3DS le fait progresser localement ; réémettre
                # toute la liste ne ferait que réveiller son parseur JSON.
                current_content = [
                    {field: item for field, item in entry.items() if field != "age"}
                    if isinstance(entry, dict)
                    else entry
                    for entry in value
                ]
                previous_content = [
                    {field: item for field, item in entry.items() if field != "age"}
                    if isinstance(entry, dict)
                    else entry
                    for entry in previous_value
                ] if isinstance(previous_value, list) else previous_value
                if current_content == previous_content:
                    continue

            if previous_value != value:
                delta[key] = value

        return delta
    def last_state_payload(self) -> dict[str, Any]:
        """Dernier état diffusé, ou un objet vide si rien n'a encore circulé.

        L'interface s'en sert pour afficher volume, média et sortie audio sans
        provoquer de nouvelle collecte.

        La copie est profonde d'un niveau : une copie superficielle laisserait
        `media` partagé avec l'état vivant du serveur, que la collecte mute pour
        y placer le jeton de pochette.
        """
        payload = self._last_payload or {}
        return {
            key: dict(value) if isinstance(value, dict) else value
            for key, value in payload.items()
        }

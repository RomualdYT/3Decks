"""Points d'accès de l'interface de configuration.

Le contrat est volontairement réduit : l'interface lit un schéma décrivant ce
qui est configurable, lit et écrit la configuration, et consulte l'état courant.
Rien de plus. Toute la validation reste celle de `config.parse`, qui fait déjà
autorité pour la console ; l'interface n'en possède aucune copie.

L'écriture ne redémarre pas l'agent : `Server.reload_config_if_changed` détecte
le fichier modifié au cycle suivant et rediffuse la mise en page aux consoles.
L'interface n'a donc qu'à enregistrer.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import asyncio
from typing import Any

from .. import config as config_module
from .. import keys as keys_module
from ..platforms.base import Capabilities, fields_of
from ..obs import ObsError, test_connection
from .http import HttpError, Request, Response


def build_schema(
    capabilities: Capabilities, obs_enabled: bool = False
) -> dict[str, Any]:
    """Décrit ce que l'interface peut proposer, capacités comprises.

    Le schéma est engendré depuis les tables de `config.py` : la liste des
    actions, les limites et les capacités ne sont donc jamais recopiées dans
    l'interface.

    En revanche l'éditeur conserve ses propres libellés et descriptions
    (`ACTIONS`, `dashboardLabel`, `capabilityLabel` dans `app.js`) : ajouter
    une action à `KNOWN_ACTIONS` la fait apparaître dans le sélecteur, mais
    sous son identifiant brut jusqu'à ce qu'un libellé lui soit donné. Un test
    vérifie que ces tables restent complètes.
    """
    available = capabilities.as_payload()
    # OBS est transversal aux plateformes : son support depend de la
    # configuration, pas de macOS ou Windows.
    available["obs"] = obs_enabled

    actions = []
    for kind in sorted(config_module.KNOWN_ACTIONS):
        needed = config_module.ACTION_CAPABILITY.get(kind)
        actions.append(
            {
                "kind": kind,
                "requires": config_module.ACTION_REQUIRED_ARG.get(kind),
                "arguments": config_module.action_arguments(kind),
                # `None` signifie « aucune capacité requise » : l'action est
                # traitée par la console ou reste sans effet par nature.
                "capability": needed,
                "supported": True if needed is None else available.get(needed, False),
            }
        )

    dashboards = []
    for name in sorted(config_module.DASHBOARDS):
        needed = config_module.DASHBOARD_CAPABILITY.get(name)
        dashboards.append(
            {
                "name": name,
                "capability": needed,
                "supported": True if needed is None else available.get(needed, False),
            }
        )

    return {
        "actions": actions,
        "dashboards": dashboards,
        "icons": sorted(config_module.ICONS),
        # Touches assignables, pour que l'éditeur les propose au lieu de
        # laisser l'utilisateur en deviner l'orthographe. Les libellés sont
        # fournis dans les deux langues : la langue est un choix d'affichage
        # côté navigateur, jamais une clé d'identification.
        "keys": {
            "modifiers": [
                {
                    "name": modifier.name,
                    "label_en": modifier.label_en,
                    "label_fr": modifier.label_fr,
                }
                for modifier in keys_module.MODIFIERS
            ],
            "groups": list(keys_module.GROUPS),
            "keys": [
                {
                    "name": key.name,
                    "label_en": key.label_en,
                    "label_fr": key.label_fr,
                    "group": key.group,
                }
                for key in keys_module.KEYS
            ],
        },
        "locales": list(config_module.LOCALES),
        "capabilities": available,
        "limits": {
            "pages": config_module.MAX_PAGES,
            "buttons_per_page": config_module.MAX_BUTTONS_PER_PAGE,
            "label": config_module.MAX_LABEL,
            "id": config_module.MAX_ID,
            "list_entries": config_module.MAX_LIST_ENTRIES,
            # Bornes du validateur, exposées pour que l'éditeur refuse les
            # mêmes valeurs que l'agent au lieu de les recopier.
            "port": list(config_module.PORT_RANGE),
            "poll_interval": list(config_module.POLL_INTERVAL_RANGE),
            "volume_step": list(config_module.VOLUME_STEP_RANGE),
            "obs_timeout": list(config_module.OBS_TIMEOUT_RANGE),
        },
        #: Valeurs par défaut, pour que l'éditeur n'en garde pas de copie.
        "defaults": {
            "host": config_module.Config().host,
            "port": config_module.Config().port,
            "poll_interval": config_module.Config().poll_interval,
            "volume_step": config_module.Config().volume_step,
            "obs_host": config_module.ObsConfig().host,
            "obs_port": config_module.ObsConfig().port,
            "obs_timeout": config_module.ObsConfig().timeout,
            "button_color": config_module.DEFAULT_BUTTON_COLOR,
        },
        "layouts": ["grid", "list"],
        "sources": ["", "windows"],
    }


class Api:
    """Regroupe les points d'accès autour du serveur de l'agent."""

    def __init__(self, server: Any) -> None:
        # Typé souplement : importer `Server` créerait un cycle, puisque le
        # serveur détient l'interface.
        self.server = server

    def routes(self) -> dict[tuple[str, str], Any]:
        return {
            ("GET", "/api/schema"): self.get_schema,
            ("GET", "/api/config"): self.get_config,
            ("PUT", "/api/config"): self.put_config,
            ("POST", "/api/config/validate"): self.validate_config,
            ("POST", "/api/obs/test"): self.test_obs,
            ("GET", "/api/state"): self.get_state,
        }

    # --- Schéma ----------------------------------------------------------------

    async def get_schema(self, request: Request) -> Response:
        return Response.json(
            build_schema(
                self.server.platform.capabilities(), self.server.config.obs.enabled
            )
        )

    async def test_obs(self, request: Request) -> Response:
        """Teste les reglages saisis et renvoie les scenes utilisables."""
        raw = request.json()
        try:
            config = config_module.parse_obs(raw)
        except config_module.ConfigError as error:
            raise HttpError(422, str(error)) from error

        try:
            status = await asyncio.to_thread(test_connection, config)
        except ObsError as error:
            raise HttpError(409, str(error)) from error
        return Response.json(status.as_payload())

    # --- Configuration ---------------------------------------------------------

    async def get_config(self, request: Request) -> Response:
        """Configuration en cours, sous la forme même du fichier.

        `scripts` est renvoyé pour affichage et pour que l'interface puisse
        proposer les noms déclarés, mais ne sera pas relu en écriture.
        """
        return Response.json(
            {
                "config": config_module.to_raw(self.server.config),
                "path": str(self.server.config_path or ""),
            }
        )

    async def put_config(self, request: Request) -> Response:
        """Valide puis enregistre la configuration.

        La révision est incrémentée d'office : sans cela, la console garderait
        sa mise en page en cache, l'utilisateur ne verrait aucun changement et
        conclurait à tort que l'enregistrement a échoué.
        """
        if self.server.config_path is None:
            raise HttpError(409, "aucun fichier de configuration a enregistrer")

        raw = request.json()
        if not isinstance(raw, dict):
            raise HttpError(400, "un objet est attendu")

        candidate = self._prepare(raw)

        try:
            parsed = config_module.parse(candidate)
        except config_module.ConfigError as error:
            # 422 plutôt que 400 : la requête est bien formée, c'est son
            # contenu que le validateur refuse. L'interface affiche le message.
            raise HttpError(422, str(error)) from error

        try:
            config_module.save(parsed, self.server.config_path)
        except OSError as error:
            raise HttpError(500, f"ecriture impossible : {error}") from error

        self.server.log(
            f"Configuration enregistree depuis l'interface "
            f"(revision {parsed.revision}, {len(parsed.pages)} pages)"
        )

        return Response.json(
            {"saved": True, "config": config_module.to_raw(parsed)}
        )

    async def validate_config(self, request: Request) -> Response:
        """Valide sans enregistrer, pour un retour au fil de la saisie."""
        raw = request.json()
        if not isinstance(raw, dict):
            raise HttpError(400, "un objet est attendu")

        try:
            config_module.parse(self._prepare(raw))
        except config_module.ConfigError as error:
            return Response.json({"valid": False, "error": str(error)})

        return Response.json({"valid": True, "error": ""})

    def _prepare(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Réinjecte les champs que l'interface n'a pas le droit de définir.

        `scripts` est repris de la configuration en cours et jamais de la
        requête : c'est la seule section décrivant des commandes exécutables,
        et l'accepter depuis un navigateur ferait de l'interface un vecteur
        d'exécution de code. Elle s'édite dans le fichier.
        """
        candidate = dict(raw)
        current = self.server.config

        candidate["scripts"] = {
            name: list(command) for name, command in current.scripts.items()
        }

        revision = candidate.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool):
            revision = current.revision
        candidate["revision"] = revision + 1

        return candidate

    # --- État ------------------------------------------------------------------

    async def get_state(self, request: Request) -> Response:
        """État courant : consoles, capacités, adresse d'appairage, journal.

        Aucune mesure n'est déclenchée ici : on rend la dernière collecte de la
        boucle de l'agent. Interroger le système à chaque requête de l'interface
        multiplierait les appels AppleScript sans bénéfice.
        """
        server = self.server
        capabilities = server.platform.capabilities()
        available = capabilities.as_payload()
        available["obs"] = server.config.obs.enabled

        return Response.json(
            {
                "version": getattr(server, "version", ""),
                "platform": server.platform.name,
                "listen": f"{server.config.host}:{server.config.port}",
                "hints": server.local_addresses(),
                "token_set": bool(server.config.token),
                "clients": [
                    {"id": client.id, "address": client.address}
                    for client in sorted(server.clients, key=lambda item: item.id)
                    if client.authenticated
                ],
                "capabilities": available,
                "snapshot": server.last_state_payload(),
                "logs": server.recent_logs(),
            }
        )

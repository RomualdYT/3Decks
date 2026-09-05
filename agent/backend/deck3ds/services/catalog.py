"""Catalog shared with the editor; distinct from the HTTP OpenAPI schema."""

from __future__ import annotations
from typing import Any
from .. import config as config_module, keys as keys_module
from ..feature_catalog import FEATURE_SPECS
from ..platforms.base import Capabilities


def effective_capabilities(
    capabilities: Capabilities, features: config_module.FeaturesConfig
) -> dict[str, bool]:
    """Capacités de la machine, masquées par les choix de l'utilisateur."""
    available = capabilities.as_payload()
    for key, feature_spec in FEATURE_SPECS.items():
        if feature_spec.capability is not None and not getattr(features, key):
            available[feature_spec.capability] = False
    # Le volume du lecteur dépend du même fournisseur que les informations
    # multimédia, même s'il possède sa propre capacité d'exécution.
    if not features.media:
        available["app_volume"] = False
    return available


def build_schema(
    capabilities: Capabilities,
    obs_enabled: bool = False,
    features: config_module.FeaturesConfig | None = None,
    platform: str = "",
) -> dict[str, Any]:
    """Décrit ce que l'interface peut proposer, capacités comprises.

    Le schéma est engendré depuis le catalogue unique : contrat, capacités,
    libellés et apparence restent donc alignés avec le validateur.
    """
    feature_config = features or config_module.FeaturesConfig()
    hardware = capabilities.as_payload()
    available = effective_capabilities(capabilities, feature_config)
    # OBS est transversal aux plateformes : son support depend de la
    # configuration, pas de macOS ou Windows.
    available["obs"] = obs_enabled

    actions = []
    for kind, spec in sorted(config_module.ACTION_SPECS.items()):
        needed = spec.capability
        item: dict[str, Any] = {
            "kind": kind,
            "requires": config_module.ACTION_REQUIRED_ARG.get(kind),
            "arguments": config_module.action_arguments(kind),
            # `None` signifie « aucune capacité requise » : l'action est
            # traitée par la console ou reste sans effet par nature.
            "capability": needed,
            "supported": True if needed is None else available.get(needed, False),
        }
        item.update(spec.presentation_payload())
        actions.append(item)

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

    feature_items = []
    for key, feature_spec in FEATURE_SPECS.items():
        item = feature_spec.as_payload()
        supported_platform = not platform or platform in feature_spec.platforms
        capability_available = (
            True
            if feature_spec.capability is None
            else hardware.get(feature_spec.capability, False)
        )
        item.update(
            {
                "enabled": getattr(feature_config, key),
                "available": supported_platform and capability_available,
            }
        )
        feature_items.append(item)

    return {
        "actions": actions,
        "dashboards": dashboards,
        "icons": sorted(config_module.ICONS),
        # Touches assignables, pour que l'éditeur les propose au lieu de
        # laisser l'utilisateur en deviner l'orthographe. Les libellés sont
        # fournis dans les deux langues : la langue est un choix d'affichage
        # côté navigateur, jamais une clé d'identification.
        "keys": keys_module.catalog(),
        "locales": list(config_module.LOCALES),
        "capabilities": available,
        "features": feature_items,
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

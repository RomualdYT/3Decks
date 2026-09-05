"""Validation of the shared configuration contract."""

from __future__ import annotations

from typing import Any

from .models import (
    FEATURE_SPECS,
    OBS_TIMEOUT_RANGE,
    POLL_INTERVAL_RANGE,
    Config,
    ConfigError,
    FeaturesConfig,
    ObsConfig,
)
from .pages import _check_references, _parse_pages
from .primitives import (
    _require_host,
    _require_int,
    _require_port,
    _require_seconds,
    _require_step,
)


def parse_obs(raw: Any) -> ObsConfig:
    """Valide la section OBS, reutilisee par le fichier et le test de l'UI."""
    if raw is None:
        return ObsConfig()
    if not isinstance(raw, dict):
        raise ConfigError("integrations.obs: un objet est attendu")

    defaults = ObsConfig()
    enabled = raw.get("enabled", defaults.enabled)
    if not isinstance(enabled, bool):
        raise ConfigError("integrations.obs.enabled: un booleen est attendu")

    host = _require_host(raw.get("host", defaults.host), "integrations.obs.host")
    port = _require_port(raw.get("port", defaults.port), "integrations.obs.port")

    password = raw.get("password", defaults.password)
    if not isinstance(password, str):
        raise ConfigError("integrations.obs.password: une chaine est attendue")

    timeout = _require_seconds(
        raw.get("timeout", defaults.timeout),
        "integrations.obs.timeout",
        *OBS_TIMEOUT_RANGE,
    )

    return ObsConfig(
        enabled=enabled,
        host=host,
        port=port,
        password=password,
        timeout=timeout,
    )


def _apply_server(raw: Any, config: Config) -> None:
    """Applique la section `server`, en conservant les défauts absents."""
    if raw is None:
        return
    if not isinstance(raw, dict):
        raise ConfigError("server: un objet est attendu")
    if not raw:
        return

    config.host = _require_host(raw.get("host", config.host), "server.host")
    config.port = _require_port(raw.get("port", config.port), "server.port")

    token = raw.get("token", "")
    if not isinstance(token, str):
        raise ConfigError("server.token: une chaine est attendue")
    config.token = token.strip()

    config.poll_interval = _require_seconds(
        raw.get("poll_interval", config.poll_interval),
        "server.poll_interval",
        *POLL_INTERVAL_RANGE,
    )
    config.volume_step = _require_step(
        raw.get("volume_step", config.volume_step), "server.volume_step"
    )


def _parse_scripts(raw: Any) -> dict[str, list[str]]:
    """Commandes autorisées, référencées par leur nom depuis les boutons."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError("scripts: un objet est attendu")
    if not raw:
        return {}

    scripts: dict[str, list[str]] = {}
    for name, command in raw.items():
        if not isinstance(command, list) or not command:
            raise ConfigError(
                f"scripts.{name}: une liste d'arguments non vide est attendue"
            )
        if not all(isinstance(item, str) for item in command):
            raise ConfigError(f"scripts.{name}: arguments textuels attendus")
        scripts[str(name)] = list(command)
    return scripts


def _parse_integrations(raw: Any, config: Config) -> None:
    if raw is None:
        return
    if not isinstance(raw, dict):
        raise ConfigError("integrations: un objet est attendu")
    if not raw:
        return
    if "obs" in raw:
        config.obs = parse_obs(raw["obs"])


def _parse_features(raw: Any) -> FeaturesConfig:
    """Valide les collectes optionnelles et leurs dépendances."""
    if raw is None:
        return FeaturesConfig()
    if not isinstance(raw, dict):
        raise ConfigError("features: un objet est attendu")

    unknown = set(raw) - set(FEATURE_SPECS)
    if unknown:
        raise ConfigError(f"features: options inconnues {sorted(unknown)}")

    defaults = FeaturesConfig()
    values: dict[str, bool] = {}
    for name in FEATURE_SPECS:
        value = raw.get(name, getattr(defaults, name))
        if not isinstance(value, bool):
            raise ConfigError(f"features.{name}: un booleen est attendu")
        values[name] = value

    # Une sous-fonction désactivée avec son parent est normalisée plutôt que
    # rejetée : l'interface peut conserver le choix pour le prochain réemploi.
    return FeaturesConfig(**values)


def parse(raw: Any) -> Config:
    """Valide une structure déjà décodée et retourne la configuration.

    Chaque section est validée par une fonction dédiée ; ne subsiste ici que
    l'enchaînement, et les vérifications qui exigent la configuration complète.
    """
    if not isinstance(raw, dict):
        raise ConfigError("la racine doit etre un objet")

    config = Config()
    _apply_server(raw.get("server", {}), config)
    config.revision = _require_int(raw.get("revision", 1), "revision")
    config.features = _parse_features(raw.get("features", {}))
    _parse_integrations(raw.get("integrations", {}), config)
    config.scripts = _parse_scripts(raw.get("scripts", {}))
    config.pages = _parse_pages(raw.get("pages", []))

    # Vérifications croisées : elles supposent toutes les pages et tous les
    # scripts déjà connus, et ne peuvent donc pas être faites plus tôt.
    _check_references(
        config.pages,
        "page.open",
        "page",
        {page.id for page in config.pages},
        "page cible '{target}' inexistante",
    )
    _check_references(
        config.pages,
        "script.run",
        "script",
        config.scripts,
        "script '{target}' non declare dans 'scripts'",
    )
    return config

"""Native implementations are chosen only at the runtime composition boundary."""

from __future__ import annotations
import sys
from ..config import Config
from ..platforms.base import Platform
from ..transports.parts import Options
from .agent import AgentRuntime


def build_platform(features: object | None = None) -> Platform:
    """Choisit l'adaptateur correspondant au système hôte."""
    if sys.platform == "darwin":
        from ..platforms.macos import MacPlatform

        return MacPlatform(features)

    if sys.platform in ("win32", "cygwin"):
        from ..platforms.windows import WindowsPlatform

        return WindowsPlatform(features)

    # Aucun adaptateur : l'agent démarre quand même, mais les actions
    # échoueront avec un message explicite plutôt qu'en silence.
    print(
        f"Attention : plateforme '{sys.platform}' non prise en charge, "
        "les actions systeme seront indisponibles.",
        file=sys.stderr,
    )
    return Platform()


def create_runtime(config: Config, options: Options) -> AgentRuntime:
    platform = build_platform(config.features)
    try:
        return AgentRuntime(config, platform, options)
    except BaseException:
        platform.close()
        raise

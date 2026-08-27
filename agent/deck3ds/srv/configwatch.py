"""Surveillance du fichier de configuration et pages dynamiques."""

from __future__ import annotations

import asyncio
from typing import Any

from .. import messages
from .. import config as config_module
from .parts import _window_buttons, _window_entries


class ConfigWatchMixin:
    def _config_stamp(self) -> float:
        """Date de modification du fichier de configuration, 0 si indisponible."""
        if self.config_path is None:
            return 0.0
        try:
            return self.config_path.stat().st_mtime
        except OSError:
            return 0.0

    def _install_config(self, loaded: config_module.Config) -> None:
        """Installe une configuration déjà validée dans tous ses consommateurs."""
        self.config = loaded
        self.dispatcher.set_config(loaded)
        self._published_windows = []
        self._config_mtime = self._config_stamp()

    def reload_config_if_changed(self) -> bool:
        """Recharge la configuration si le fichier a été modifié.

        Sans cela, un agent démarré avant une modification continuerait de
        servir l'ancienne mise en page : le fichier semblerait à jour alors que
        la console recevrait une version périmée. C'est une source de confusion
        difficile à diagnostiquer.
        """
        if self.config_path is None:
            return False

        stamp = self._config_stamp()
        if stamp == 0.0 or stamp == self._config_mtime:
            return False

        self._config_mtime = stamp

        try:
            loaded = config_module.load(self.config_path)
        except config_module.ConfigError as error:
            # Une erreur de saisie ne doit pas interrompre le service : on
            # signale et on conserve la configuration en cours.
            self.log(f"Configuration invalide, ancienne version conservee : {error}")
            return False

        self._install_config(loaded)
        self.log(f"Configuration rechargee ({len(loaded.pages)} pages)")
        return True

    async def apply_config(self, loaded: config_module.Config) -> None:
        """Applique puis diffuse immédiatement une sauvegarde de l'interface.

        Le surveillant de fichier reste utile pour les éditions manuelles, mais
        l'API ne doit pas rendre la main avec un fichier plus récent que l'état
        réellement servi aux consoles.
        """
        self._install_config(loaded)

        if self._has_dynamic_pages():
            try:
                windows = await asyncio.to_thread(self.platform.list_windows)
                active = await asyncio.to_thread(self.platform.get_active_app)
                self._fill_dynamic_pages(windows, active)
            except Exception as error:
                # La configuration statique reste valide et doit être diffusée ;
                # la prochaine collecte retentera de produire le contenu.
                self.debug(
                    "pages dynamiques indisponibles apres sauvegarde: "
                    f"{type(error).__name__}: {error}"
                )

        await self._broadcast(self._config_message())

    def _has_dynamic_pages(self) -> bool:
        return any(page.source == "windows" for page in self.config.pages)

    def _fill_dynamic_pages(
        self, windows: list[tuple[str, str]], active_app: str = ""
    ) -> None:
        """Remplit les pages alimentées automatiquement.

        Selon la présentation choisie, la page reçoit soit une liste défilante,
        soit une grille limitée à six boutons.
        """
        for page in self.config.pages:
            if page.source != "windows":
                continue

            if page.layout == "list":
                page.entries = _window_entries(windows, active_app)
            else:
                page.buttons = _window_buttons(windows)

        # Le dispatcher partage la configuration : il retrouvera ainsi les
        # boutons générés lors de la résolution d'un appui.
        self.dispatcher.set_config(self.config)
        self._published_windows = list(windows)

    def _config_message(self) -> dict[str, Any]:
        """Configuration à transmettre, pages dynamiques comprises."""
        return self.config.snapshot_payload(messages.language())

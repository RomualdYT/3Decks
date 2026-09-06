"""Resolved console view. Generated contents never mutate the stored document."""

from __future__ import annotations
from typing import Any
from ..config import Config
from ..extensions.bridge import config_message, fill_sources
from .parts import _window_buttons, _window_entries
from .ports import AgentPort


class ConsoleConfiguration:
    def __init__(self, context: AgentPort) -> None:
        self.context = context

    def install(self, loaded: Config) -> None:
        self.context.config = loaded
        self.context.platform.configure_features(loaded.features)
        self.context.dispatcher.set_config(loaded)
        self.context._published_windows = []
        fill_sources(self.context.extensions, loaded)

    async def publish(self) -> None:
        if self._has_dynamic_pages():
            try:
                windows = await self.context.native_pool.run(
                    self.context.platform.list_windows
                )
                active = await self.context.native_pool.run(
                    self.context.platform.get_active_app
                )
                self._fill_dynamic_pages(windows, active)
            except Exception:
                self.context.debug(
                    "Dynamic pages unavailable; retrying on the next collection"
                )
        await self.context._broadcast_config()

    def _has_dynamic_pages(self) -> bool:
        return self.context.config.features.windows and any(
            page.source == "windows" for page in self.context.config.pages
        )

    def _fill_dynamic_pages(
        self, windows: list[tuple[str, str]], active_app: str = ""
    ) -> None:
        for page in self.context.config.pages:
            if page.source == "windows":
                if page.layout == "list":
                    page.entries = _window_entries(windows, active_app)
                else:
                    page.buttons = _window_buttons(windows)
        self.context.dispatcher.set_config(self.context.config)
        self.context._published_windows = list(windows)

    def _config_message(self, locale: str = "en") -> dict[str, Any]:
        return dict(
            config_message(self.context.extensions, self.context.config, locale)
        )

    async def _broadcast_config(self) -> None:
        for client in self.context._audience():
            if not await client.send(
                self._config_message(getattr(client, "language", "en"))
            ):
                await self.context._drop(client)

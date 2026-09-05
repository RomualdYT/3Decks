"""Compatibility entry point; implementation is composed by AgentRuntime."""

from .runtime.agent import AgentRuntime

from .transports.parts import (
    _APP_STYLES as _APP_STYLES,
    _DEFAULT_STYLE as _DEFAULT_STYLE,
    _icon_for as _icon_for,
    _snapshot_payload as _snapshot_payload,
    _window_buttons as _window_buttons,
    _window_entries as _window_entries,
    ArtworkCache as ArtworkCache,
    Client as Client,
    Options as Options,
)
from .version import VERSION as VERSION

Server = AgentRuntime

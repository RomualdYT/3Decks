"""The only application dependency exposed to HTTP adapters."""

from dataclasses import dataclass
from .configuration import ConfigService
from .devices import DeviceService
from .extensions import ExtensionService
from .state import StateService
from .system import SystemService


@dataclass(frozen=True)
class Services:
    config: ConfigService
    state: StateService
    system: SystemService
    extensions: ExtensionService
    devices: DeviceService

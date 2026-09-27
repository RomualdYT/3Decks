"""Native desktop host for the graphical 3Decks entry point.

Nothing in this package is imported by the headless ``deck3ds`` command.  The
system-tray dependency and its GUI loop therefore remain an optional edge
around the agent runtime instead of leaking into the domain or HTTP layers.
"""

from .application import DesktopOptions, run_desktop

__all__ = ["DesktopOptions", "run_desktop"]

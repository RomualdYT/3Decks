"""Compatibility package for running the source tree without installation.

The implementation lives in ``agent/backend/deck3ds``. Extending the package
search path keeps the public ``python3 -m deck3ds`` command unchanged while
allowing the repository to separate backend and frontend sources cleanly.
"""

from pathlib import Path

_BACKEND_PACKAGE = Path(__file__).resolve().parent.parent / "backend" / "deck3ds"
__path__.append(str(_BACKEND_PACKAGE))


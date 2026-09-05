"""Neutral validation and normalization for action arguments.

This module belongs to the configuration/domain layer.  Platform adapters and
configuration parsing can therefore share the exact same rules without making
the domain depend on an operating-system adapter.
"""

from __future__ import annotations

from urllib.parse import urlsplit


class WebUrlError(ValueError):
    """A URL is malformed or is not an explicitly supported web URL."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def normalize_web_url(value: str) -> str:
    """Return a canonical HTTP(S) target or reject an ambiguous value."""
    candidate = value.strip()
    if (
        not candidate
        or len(candidate) > 2048
        or any(ord(character) < 32 or ord(character) == 127 for character in candidate)
    ):
        raise WebUrlError("invalid_url")
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    try:
        parsed = urlsplit(candidate)
        hostname = parsed.hostname
        # Accessing the property validates an eventual out-of-range port.
        parsed.port
    except ValueError as error:
        raise WebUrlError("invalid_url") from error
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not hostname
        or any(character.isspace() for character in parsed.netloc)
    ):
        raise WebUrlError("http_only")
    return candidate

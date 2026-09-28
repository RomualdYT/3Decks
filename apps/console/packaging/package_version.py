"""Encode a release tag as the 16-bit CIA title version, without silent wrap."""
import re
import sys


def encode(tag: str) -> int:
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        raise ValueError("Console releases require a stable vMAJOR.MINOR.PATCH tag")
    major, minor, patch = map(int, match.groups())
    if major > 63 or minor > 63 or patch > 15:
        raise ValueError("CIA version limits: major <= 63, minor <= 63, patch <= 15")
    return major * 1024 + minor * 16 + patch


if __name__ == "__main__":
    print(f"APP_VERSION={encode(sys.argv[1])}")

"""Import boundaries are executable rules, not just documentation."""

import ast
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1] / "backend" / "deck3ds"


def imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ""


@pytest.mark.parametrize("layer", ["services", "configuration", "extensions"])
def test_domain_layers_do_not_import_http_or_runtime(layer):
    for source in (PACKAGE / layer).glob("*.py"):
        forbidden = {
            name
            for name in imports(source)
            if name.split(".")[0]
            in {
                "fastapi",
                "starlette",
                "uvicorn",
                "api",
                "runtime",
                "transports",
                "server",
            }
        }
        assert not forbidden, (source, forbidden)


def test_api_routes_only_consume_services_not_global_server():
    for source in (PACKAGE / "api" / "routes").glob("*.py"):
        forbidden = {
            name
            for name in imports(source)
            if name.split(".")[0] in {"runtime", "server", "transports", "platforms"}
        }
        assert not forbidden, (source, forbidden)


def test_configuration_domain_does_not_import_platform_adapters():
    for source in (PACKAGE / "configuration").glob("*.py"):
        forbidden = {
            name for name in imports(source) if name.split(".")[0] == "platforms"
        }
        assert not forbidden, (source, forbidden)

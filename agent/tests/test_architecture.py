"""Import boundaries are executable rules, not just documentation."""

import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1] / "backend" / "deck3ds"


def import_names(source, package):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                module = resolve_name("." * node.level + module, package)
            yield module
            yield from (f"{module}.{alias.name}" for alias in node.names)


def imports(path):
    package = ".".join(("deck3ds", *path.relative_to(PACKAGE).parent.parts))
    for name in import_names(path.read_text(encoding="utf-8"), package):
        yield name.removeprefix("deck3ds.")


@pytest.mark.parametrize("statement", [
    "import deck3ds.api", "from deck3ds import api",
    "from .. import api", "from ..api import app",
])
def test_boundary_inspection_recognizes_absolute_and_relative_imports(statement):
    names = list(import_names(statement, "deck3ds.services"))
    assert any(name == "deck3ds.api" or name.startswith("deck3ds.api.") for name in names)


@pytest.mark.parametrize("layer", ["services", "configuration", "extensions"])
def test_domain_layers_do_not_import_http_or_runtime(layer):
    for source in (PACKAGE / layer).rglob("*.py"):
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
    for source in (PACKAGE / "api" / "routes").rglob("*.py"):
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

"""ASGI-level boundaries supplement the real-Uvicorn contract suite."""

import asyncio
import gc
import json
import weakref
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from deck3ds.api.app import create_app
from deck3ds.api.export import specification
from deck3ds.api.security import (
    HttpSettings,
    LocalSecurity,
    MAX_BODY,
    MAX_HEADER,
    local_origin,
)

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    "path",
    ["schema", "config", "state", "apps", "extensions", "health", "openapi.json"],
)
async def test_reads_are_json_authenticated_and_uncached(client, path):
    response = await client.get("/api/" + path)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), dict)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


@pytest.mark.parametrize(
    "path", ["/api", "/api/", "/api/missing", "/api/openapi.json", "/api/health"]
)
async def test_unknown_paths_do_not_bypass_auth(client, path):
    response = await client.get(path, headers={"X-Deck3DS-Token": "wrong"})
    assert response.status_code == 403
    assert response.json()["code"] == "invalid_session"
    assert response.json()["request_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize(
    "host",
    [
        "evil.example",
        "localhost@evil.example",
        "localhost:abc",
        "localhost:99999",
        "localhost/path",
        "localhost#x",
        "",
        "[::1",
    ],
)
async def test_host_validation(client, host):
    response = await client.get("/api/state", headers={"host": host})
    assert response.status_code == 403
    assert response.json()["code"] == "host_refused"


@pytest.mark.parametrize(
    "origin",
    [
        "https://127.0.0.1:4173",
        "http://evil:4173",
        "http://127.0.0.1",
        "http://127.0.0.1:4173/path",
        "http://user@localhost:4173",
    ],
)
async def test_development_origin_configuration_rejects_unsafe_values(origin):
    with pytest.raises(ValueError):
        local_origin(origin)


async def test_development_origin_is_explicit_not_a_production_default(agent, client):
    headers = {"Origin": "http://127.0.0.1:4173"}
    refused = await client.post("/api/pairing/rotate", headers=headers)
    assert refused.status_code == 403
    assert refused.json()["code"] == "origin_refused"
    app = create_app(
        agent.services, HttpSettings(token="session", dev_origins=(headers["Origin"],))
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1"
    ) as dev:
        response = await dev.post(
            "/api/pairing/rotate", headers={**headers, "X-Deck3DS-Token": "session"}
        )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    "method,path,status",
    [
        ("DELETE", "/api/config", 405),
        ("GET", "/api/missing", 404),
        ("GET", "/docs", 404),
        ("GET", "/redoc", 404),
    ],
)
async def test_missing_routes_and_methods(client, method, path, status):
    response = await client.request(method, path)
    assert response.status_code == status
    assert set(response.json()) == {"error", "code", "request_id"}


@pytest.mark.parametrize(
    "payload,status", [(b"{broken", 400), (b"", 400), (b'{"kind":"SECRET"}', 422)]
)
async def test_validation_errors_do_not_echo_inputs(client, payload, status):
    response = await client.post(
        "/api/paths/pick", content=payload, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == status
    assert "SECRET" not in response.text
    assert "input" not in response.json()


async def test_static_assets_head_cache_mime_and_symlink_containment(agent, tmp_path):
    root = tmp_path / "static"
    root.mkdir()
    (root / "assets").mkdir()
    (root / "index.html").write_text(
        "<!doctype html><title>Local</title>", encoding="utf-8"
    )
    (root / "assets" / "app-Abcd1234.js").write_text(
        "export default 1", encoding="utf-8"
    )
    (root / "logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8"
    )
    outside = tmp_path / "secret.txt"
    outside.write_text("never serve", encoding="utf-8")
    try:
        (root / "escape.txt").symlink_to(outside)
        symlinks = True
    except OSError:  # Windows without developer-mode symlink privileges.
        symlinks = False
    app = create_app(agent.services, static_root=root)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1"
    ) as static:
        for path, content_type, immutable in [
            ("/", "text/html", False),
            ("/logo.svg", "image/svg+xml", False),
            ("/assets/app-Abcd1234.js", "javascript", True),
        ]:
            get = await static.get(path)
            head = await static.head(path)
            assert get.status_code == head.status_code == 200
            assert not head.content
            assert head.headers["content-length"] == get.headers["content-length"]
            assert content_type in get.headers["content-type"]
            assert ("immutable" in get.headers["cache-control"]) is immutable
        if symlinks:
            assert (await static.get("/escape.txt")).status_code == 403
        assert (await static.get("/..%2fsecret.txt")).status_code == 403


async def invoke_envelope(*, headers=(), chunks=(), timeout=0.1, delay=0, failure=None):
    sent = []
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/test",
        "raw_path": b"/api/test",
        "query_string": b"",
        "headers": [
            (b"host", b"127.0.0.1"),
            (b"x-deck3ds-token", b"session"),
            *headers,
        ],
    }
    messages = iter(chunks)

    async def receive():
        if delay:
            await asyncio.sleep(delay)
        return next(messages, {"type": "http.request", "body": b"", "more_body": False})

    async def send(message):
        sent.append(message)

    async def app(_scope, receive, send):
        if failure:
            raise failure
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    await LocalSecurity(
        app, HttpSettings(token="session", body_timeout=timeout), lambda _: None
    )(scope, receive, send)
    return sent


@pytest.mark.parametrize(
    "headers,code",
    [
        ([(b"content-length", b"-1")], "body_too_large"),
        ([(b"content-length", b"invalid")], "invalid_body"),
        ([(b"content-length", str(MAX_BODY + 1).encode())], "body_too_large"),
        ([(b"x-large", b"x" * MAX_HEADER)], "headers_too_large"),
        ([(b"host", b"localhost")], "ambiguous_headers"),
    ],
)
async def test_asgi_header_limits(headers, code):
    messages = await invoke_envelope(headers=headers)
    assert json.loads(messages[-1]["body"])["code"] == code


async def test_chunked_body_limit_and_slow_receiver():
    chunks = [
        {"type": "http.request", "body": b"x" * (MAX_BODY // 2 + 1), "more_body": True}
    ] * 2
    large = await invoke_envelope(chunks=chunks)
    assert large[0]["status"] == 413
    slow = await invoke_envelope(timeout=0.001, delay=0.05)
    assert json.loads(slow[-1]["body"])["code"] == "body_timeout"
    assert await invoke_envelope(chunks=[{"type": "http.disconnect"}]) == []


async def test_unexpected_error_is_redacted():
    messages = await invoke_envelope(failure=RuntimeError("password=PRIVATE"))
    assert messages[0]["status"] == 500
    assert "PRIVATE" not in str(messages)


async def test_factory_export_is_deterministic_and_does_not_start_core():
    with patch(
        "deck3ds.runtime.agent.AgentRuntime.__init__",
        side_effect=AssertionError("must not construct"),
    ):
        first = specification()
        assert first == specification()
    document = json.loads(first)
    assert document["security"] == [{"LocalSession": []}]
    assert len(document["paths"]) == 13
    artwork = document["paths"]["/api/artwork"]["get"]["responses"]
    assert "image/png" in artwork["200"]["content"]
    assert "204" in artwork
    exported = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"
    assert exported.read_text(encoding="utf-8") == first


async def test_http_lifespan_does_not_own_runtime(agent):
    app = create_app(agent.services)
    async with app.router.lifespan_context(app):
        assert app.state.http_ready
        assert not agent._closed
    assert not app.state.http_ready
    assert not agent._closed


async def test_factory_does_not_retain_closed_applications():
    references = []
    for _ in range(3):
        app = create_app()
        app.openapi()  # Resolve every route and response model, as a real API does.
        references.append(weakref.ref(app))
    del app
    gc.collect()
    assert all(reference() is None for reference in references)


async def test_unwired_app_fails_explicitly():
    app = create_app(settings=HttpSettings(token="session"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1"
    ) as client:
        response = await client.get(
            "/api/config", headers={"X-Deck3DS-Token": "session"}
        )
    assert response.status_code == 503

"""ASGI envelope: local-only session, origin checks and bounded request bodies."""

from __future__ import annotations
import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from ..services.errors import ServiceError

MAX_BODY = 512 * 1024
MAX_HEADER = 16 * 1024
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
SECURITY_HEADERS = {
    "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}


def local_origin(origin: str) -> str:
    try:
        value = urlsplit(origin)
        if (
            value.scheme != "http"
            or value.hostname not in LOCAL_HOSTS
            or value.port is None
        ):
            raise ValueError
        if (
            value.username
            or value.password
            or value.path
            or value.query
            or value.fragment
        ):
            raise ValueError
    except ValueError as error:
        raise ValueError(
            "A development origin must be an explicit http://loopback:port origin"
        ) from error
    return origin


@dataclass(frozen=True)
class HttpSettings:
    port: int = 38124
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24), repr=False)
    dev_origins: tuple[str, ...] = ()
    body_timeout: float = 15.0

    def __post_init__(self) -> None:
        for origin in self.dev_origins:
            local_origin(origin)


class LocalSecurity:
    def __init__(
        self, app: ASGIApp, settings: HttpSettings, log: Callable[[str], None]
    ) -> None:
        self.app, self.settings, self.log = app, settings, log

    def check(self, scope: Scope) -> None:
        pairs = scope.get("headers", [])
        if (
            sum(len(key) + len(value) + 4 for key, value in pairs)
            + len(scope.get("raw_path", b""))
            + len(scope.get("query_string", b""))
            > MAX_HEADER
        ):
            raise ServiceError(413, "en-tetes trop longs", "headers_too_large")
        headers = dict(pairs)
        for name in (b"host", b"origin", b"x-deck3ds-token", b"content-length"):
            if sum(key == name for key, _ in pairs) > 1:
                raise ServiceError(400, "en-tete duplique", "ambiguous_headers")
        try:
            host = headers.get(b"host", b"").decode("latin1")
            parsed = urlsplit("http://" + host)
            if (
                parsed.hostname not in LOCAL_HOSTS
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError
            parsed.port  # Validate a supplied port, without requiring one for HTTP/1.0 compatibility.
        except ValueError as error:
            raise ServiceError(403, "hote refuse", "host_refused") from error
        if scope["path"] == "/api" or scope["path"].startswith("/api/"):
            token = headers.get(b"x-deck3ds-token", b"").decode("latin1")
            if not token:
                query = parse_qs(scope.get("query_string", b"").decode("latin1"))
                token = query.get("token", [""])[0]
            if not secrets.compare_digest(
                token.encode("utf-8"), self.settings.token.encode("utf-8")
            ):
                raise ServiceError(403, "jeton absent ou invalide", "invalid_session")
            if scope["method"] not in ("GET", "HEAD"):
                origin = headers.get(b"origin", b"").decode("latin1")
                allowed = {
                    f"http://127.0.0.1:{self.settings.port}",
                    f"http://localhost:{self.settings.port}",
                    f"http://[::1]:{self.settings.port}",
                    *self.settings.dev_origins,
                }
                if origin and origin not in allowed:
                    raise ServiceError(403, "origine refusee", "origin_refused")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started = False

        async def protected_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = list(message.get("headers", []))
                names = {key.lower() for key, _ in headers}
                headers.extend(
                    (key.encode(), value.encode())
                    for key, value in SECURITY_HEADERS.items()
                    if key.encode() not in names
                )
                headers.append((b"x-request-id", request_id.encode()))
                if b"cache-control" not in names:
                    headers.append((b"cache-control", b"no-store"))
                message = {**message, "headers": headers}
            await send(message)

        try:
            self.check(scope)
            headers = dict(scope.get("headers", []))
            try:
                declared = int(headers.get(b"content-length", b"0"))
            except ValueError as error:
                raise ServiceError(
                    400, "content-length invalide", "invalid_body"
                ) from error
            if declared < 0 or declared > MAX_BODY:
                raise ServiceError(413, "corps trop volumineux", "body_too_large")
            body = bytearray()
            async with asyncio.timeout(self.settings.body_timeout):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > MAX_BODY:
                        raise ServiceError(
                            413, "corps trop volumineux", "body_too_large"
                        )
                    if not message.get("more_body", False):
                        break
            consumed = False

            async def buffered_receive() -> Message:
                nonlocal consumed
                if consumed:
                    return await receive()
                consumed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            await self.app(scope, buffered_receive, protected_send)
        except TimeoutError:
            if not started:
                await JSONResponse(
                    {
                        "error": "corps incomplet",
                        "code": "body_timeout",
                        "request_id": request_id,
                    },
                    status_code=400,
                )(scope, receive, protected_send)
        except ServiceError as error:
            if not started:
                await JSONResponse(
                    {
                        "error": error.message,
                        "code": error.code,
                        "request_id": request_id,
                    },
                    status_code=error.status,
                )(scope, receive, protected_send)
        except Exception as error:
            self.log(f"HTTP {request_id}: {type(error).__name__}")
            if not started:
                await JSONResponse(
                    {
                        "error": "erreur interne",
                        "code": "internal_error",
                        "request_id": request_id,
                    },
                    status_code=500,
                )(scope, receive, protected_send)

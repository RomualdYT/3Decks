"""Serveur HTTP minimal de l'interface de configuration.

Modèle de sécurité
==================

La configuration désigne des programmes à exécuter : une interface capable de
l'écrire est donc une surface d'exécution de code. Quatre protections, toutes
nécessaires, aucune suffisante seule :

1. **Écoute sur la boucle locale uniquement.** L'adresse est forcée à
   `127.0.0.1`, jamais celle du serveur de la console. Un poste du réseau ne
   peut pas atteindre l'interface.

2. **Jeton de session.** Engendré à chaque démarrage, affiché dans l'URL du
   journal. Toute requête sur `/api/` doit le présenter. Sans cela, n'importe
   quelle page web ouverte dans le navigateur pourrait écrire la configuration
   par simple requête vers `127.0.0.1` : le navigateur, lui, a bien le droit
   d'y accéder.

3. **Contrôle de l'en-tête `Host`.** Seuls `127.0.0.1` et `localhost` sont
   admis. Cela ferme la réattribution de nom de domaine : un nom contrôlé par
   un tiers qui résoudrait vers `127.0.0.1` contournerait sinon la règle
   d'origine du navigateur.

4. **Contrôle de l'`Origin` en écriture.** Une origine étrangère est refusée.

Reste une décision volontaire : la section `scripts` est en **lecture seule**.
C'est le seul endroit où l'utilisateur déclare des commandes arbitraires. La
rendre modifiable depuis un navigateur transformerait la moindre faille des
protections ci-dessus en exécution de code à distance. Elle s'édite dans le
fichier, à la main. L'interface l'affiche et permet d'y faire référence.

Pourquoi ne pas utiliser `http.server` ? Il est synchrone et bloquant. L'agent
tient sur une boucle asyncio ; y greffer un serveur à fils d'exécution
obligerait à verrouiller l'accès à la configuration partagée. Analyser une
requête HTTP suffisamment pour ce besoin tient en quelques dizaines de lignes.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs, unquote, urlsplit

#: Adresses admises dans l'en-tête `Host`.
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]", "::1"})

#: Taille maximale d'un corps de requête. Une configuration complète tient très
#: largement dedans ; au-delà, il s'agit d'une erreur ou d'un abus.
MAX_BODY = 512 * 1024

#: Garde-fou sur la ligne de requête et les en-têtes.
MAX_HEADER = 16 * 1024

#: Types de contenu servis pour l'interface statique.
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".json": "application/json; charset=utf-8",
}


class HttpError(Exception):
    """Réponse d'erreur à renvoyer tel quel au client."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class Request:
    """Requête analysée."""

    def __init__(
        self,
        method: str,
        target: str,
        headers: dict[str, str],
        body: bytes,
    ) -> None:
        self.method = method
        self.headers = headers
        self.body = body

        split = urlsplit(target)
        self.path = unquote(split.path)
        self.query = parse_qs(split.query)

    def json(self) -> Any:
        """Corps décodé. Lève `HttpError` si le contenu est illisible."""
        if not self.body:
            raise HttpError(400, "corps vide")
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise HttpError(400, f"JSON invalide : {error}") from error


class Response:
    """Réponse à sérialiser."""

    def __init__(
        self,
        status: int = 200,
        body: bytes = b"",
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        self.status = status
        self.body = body
        self.content_type = content_type

    @classmethod
    def json(cls, payload: Any, status: int = 200) -> Response:
        text = json.dumps(payload, ensure_ascii=False)
        return cls(
            status=status,
            body=text.encode("utf-8"),
            content_type="application/json; charset=utf-8",
        )


#: Une route reçoit la requête et retourne une réponse.
Handler = Callable[[Request], Awaitable[Response]]

STATUS_TEXT = {
    200: "OK",
    204: "No Content",
    301: "Moved Permanently",
    400: "Bad Request",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    413: "Payload Too Large",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
}


class UiServer:
    """Sert l'interface de configuration sur la boucle locale."""

    def __init__(
        self,
        routes: dict[tuple[str, str], Handler],
        port: int = 38124,
        log: Callable[[str], None] | None = None,
        static_root: Path | None = None,
    ) -> None:
        self.routes = routes
        self.port = port
        self.log = log or (lambda message: None)
        self.static_root = static_root or (Path(__file__).resolve().parent / "static")

        # Jeton de session : la validité d'une requête d'écriture en dépend.
        # Renouvelé à chaque démarrage, donc jamais stocké sur le disque.
        self.token = secrets.token_urlsafe(24)
        self._server: asyncio.base_events.Server | None = None

    @property
    def url(self) -> str:
        """Adresse complète à ouvrir, jeton compris."""
        return f"http://127.0.0.1:{self.port}/?token={self.token}"

    async def start(self) -> None:
        # `127.0.0.1` est délibérément codé en dur : l'interface ne doit jamais
        # suivre `server.host`, qui vaut d'ordinaire `0.0.0.0` et exposerait
        # alors l'éditeur de configuration à tout le réseau.
        self._server = await asyncio.start_server(
            self._handle, "127.0.0.1", self.port, reuse_address=True
        )
        self.log(f"Interface de configuration : {self.url}")

    async def close(self) -> None:
        if self._server is None:
            return
        self._server.close()
        try:
            await self._server.wait_closed()
        except (ConnectionError, OSError):
            pass

    # --- Analyse ---------------------------------------------------------------

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            request = await self._read_request(reader)
            if request is None:
                return
            response = await self._route(request)
        except HttpError as error:
            response = Response.json({"error": error.message}, status=error.status)
        except (ConnectionError, asyncio.IncompleteReadError):
            writer.close()
            return
        except Exception as error:  # une requête ne doit pas tuer l'agent
            self.log(f"Interface : erreur {type(error).__name__}: {error}")
            response = Response.json({"error": "erreur interne"}, status=500)

        try:
            writer.write(self._encode(response))
            await writer.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            writer.close()

    async def _read_request(self, reader: asyncio.StreamReader) -> Request | None:
        try:
            head = await asyncio.wait_for(
                reader.readuntil(b"\r\n\r\n"), timeout=10.0
            )
        except asyncio.LimitOverrunError as error:
            raise HttpError(413, "en-tetes trop longs") from error
        except (asyncio.IncompleteReadError, asyncio.TimeoutError):
            # Connexion fermée ou sonde silencieuse : rien à répondre.
            return None

        if len(head) > MAX_HEADER:
            raise HttpError(413, "en-tetes trop longs")

        lines = head.decode("latin-1").split("\r\n")
        parts = lines[0].split(" ")
        if len(parts) < 2:
            raise HttpError(400, "ligne de requete invalide")

        method, target = parts[0].upper(), parts[1]

        headers: dict[str, str] = {}
        for line in lines[1:]:
            if not line:
                continue
            name, _, value = line.partition(":")
            # Les noms d'en-tête sont insensibles à la casse.
            headers[name.strip().lower()] = value.strip()

        body = b""
        raw_length = headers.get("content-length", "")
        if raw_length:
            try:
                length = int(raw_length)
            except ValueError as error:
                raise HttpError(400, "content-length invalide") from error
            if length < 0 or length > MAX_BODY:
                raise HttpError(413, "corps trop volumineux")
            if length:
                try:
                    body = await asyncio.wait_for(
                        reader.readexactly(length), timeout=15.0
                    )
                except (asyncio.IncompleteReadError, asyncio.TimeoutError) as error:
                    raise HttpError(400, "corps incomplet") from error

        return Request(method, target, headers, body)

    def _encode(self, response: Response) -> bytes:
        reason = STATUS_TEXT.get(response.status, "Unknown")
        headers = [
            f"HTTP/1.1 {response.status} {reason}",
            f"Content-Type: {response.content_type}",
            f"Content-Length: {len(response.body)}",
            "Connection: close",
            # L'interface ne doit jamais être mise en cache : elle reflète un
            # état vivant, et une version périmée induirait en erreur.
            "Cache-Control: no-store",
            # Défense en profondeur : aucune ressource distante n'est chargée.
            "Content-Security-Policy: default-src 'self'; img-src 'self' data:",
            "X-Content-Type-Options: nosniff",
            # Empêche la fuite du jeton présent dans l'URL vers un tiers.
            "Referrer-Policy: no-referrer",
        ]
        return ("\r\n".join(headers) + "\r\n\r\n").encode("latin-1") + response.body

    # --- Sécurité et acheminement ---------------------------------------------

    def _check_host(self, request: Request) -> None:
        """Refuse un `Host` étranger, pour fermer la réattribution de nom."""
        host = request.headers.get("host", "")
        # Le port n'entre pas en compte ; l'adresse littérale IPv6 est gardée
        # entière car elle contient elle-même des deux-points.
        name = host
        if host.startswith("["):
            name = host.partition("]")[0] + "]"
        elif ":" in host:
            name = host.partition(":")[0]

        if name.lower() not in ALLOWED_HOSTS:
            raise HttpError(403, f"hote '{host}' refuse")

    def _check_origin(self, request: Request) -> None:
        """Refuse une origine étrangère sur les requêtes d'écriture."""
        origin = request.headers.get("origin", "")
        if not origin:
            # Absente sur une requête de même origine émise par notre page.
            return

        split = urlsplit(origin)
        if split.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise HttpError(403, f"origine '{origin}' refusee")
        if split.port != self.port:
            raise HttpError(403, f"origine '{origin}' refusee")

    def _check_token(self, request: Request) -> None:
        """Vérifie le jeton de session, en temps constant."""
        supplied = request.headers.get("x-deck3ds-token", "")
        if not supplied:
            values = request.query.get("token", [])
            supplied = values[0] if values else ""

        if not secrets.compare_digest(supplied, self.token):
            raise HttpError(403, "jeton absent ou invalide")

    async def _route(self, request: Request) -> Response:
        self._check_host(request)

        if request.path.startswith("/api/"):
            self._check_token(request)
            if request.method not in ("GET", "HEAD"):
                self._check_origin(request)

            handler = self.routes.get((request.method, request.path))
            if handler is None:
                # Distinguer 404 de 405 aide au diagnostic pendant le
                # développement de l'interface.
                known = any(path == request.path for _, path in self.routes)
                if known:
                    raise HttpError(405, f"methode {request.method} refusee")
                raise HttpError(404, f"route inconnue : {request.path}")

            return await handler(request)

        if request.method not in ("GET", "HEAD"):
            raise HttpError(405, f"methode {request.method} refusee")

        return self._serve_static(request.path)

    # --- Fichiers statiques ----------------------------------------------------

    def _serve_static(self, path: str) -> Response:
        relative = "index.html" if path in ("/", "") else path.lstrip("/")

        # Un chemin remontant hors du dossier servi doit être refusé avant
        # toute lecture. La comparaison porte sur le chemin résolu, seule forme
        # qui résiste aux liens symboliques comme aux séquences « .. ».
        root = self.static_root.resolve()
        target = (root / relative).resolve()

        if target != root and root not in target.parents:
            raise HttpError(403, "chemin refuse")

        if not target.is_file():
            raise HttpError(404, f"fichier absent : {relative}")

        content_type = CONTENT_TYPES.get(
            target.suffix, "application/octet-stream"
        )
        return Response(body=target.read_bytes(), content_type=content_type)

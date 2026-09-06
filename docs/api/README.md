# Local HTTP API reference

[Documentation](../README.md) · [Guide français](README.fr.md)

[OpenAPI JSON](openapi.json) is the generated contract. It is distinct from `/api/schema`, which is the dynamic editor catalog. No Swagger/ReDoc UI or CDN is required.

## Authentication and transport

The agent listens exclusively on `127.0.0.1` (default port 38124), only with `--ui`. Obtain the session token from the initial UI link, and send `X-Deck3DS-Token`. The initial `?token=...` form remains accepted. This per-start session is not the persistent console pairing token. The frontend stores it in sessionStorage before removing it from the URL.

All of `/api` and `/api/`, including unknown routes, are protected. Host must be loopback; duplicate sensitive headers are refused. Write origins, if present, must exactly match the local UI origin or an explicitly configured loopback development origin. Missing Origin remains allowed for local non-browser clients. There is no permissive CORS and proxy headers are not trusted.

Requests require JSON Content-Type when they have a JSON body. Limits: 512 KiB body, including chunked bodies; 16 KiB application header budget; 15 seconds to receive a complete body; 64 concurrent Uvicorn connections/tasks; five-second HTTP keepalive. CSP, `nosniff`, `no-referrer`, a request ID and cache policy apply to application responses. H11/Uvicorn may reject malformed HTTP or concurrency overload before the ASGI application: those low-level errors may be plain text, without the JSON envelope or request ID. Tests deliberately distinguish parser behavior from the application contract.

## Operations

| Method / path | Request | Successful result |
|---|---|---|
| `GET /api/schema` | — | Actions, capabilities, features, keys, dashboards, extension sources, defaults and limits |
| `GET /api/config` | — | `{config, path}`: the persisted document, not generated console content |
| `PUT /api/config` | Config document; retain revision from GET | `{saved: true, config}` with new revision |
| `POST /api/config/validate` | Candidate JSON | `{valid, error}`; invalid domain config is a 200 with `valid: false`, no write |
| `GET /api/state` | — | Cached state, clients, paired-device metadata, bounded logs/events and counters |
| `GET /api/artwork` | — | Cached console artwork as `image/png`, or 204 when unavailable; local session required |
| `GET /api/apps` | — | `{apps: string[]}` from an off-loop native query |
| `POST /api/paths/pick` | `{kind: "file" \| "folder"}` | `{cancelled, path, kind}`; cancellation is successful, not a failure |
| `POST /api/permissions/open` | `{permission: string}` | `{opened: true, permission}`; native adapter validates supported settings |
| `POST /api/obs/test` | OBS settings, omitted defaults allowed | `{connected: true, obs_version, current_scene, scenes}` |
| `POST /api/pairing/rotate` | No body required | `{required, code, expires_in}` |
| `DELETE /api/paired-devices/{id}` | — | `{revoked: true}`; also closes that console's active connection |
| `GET /api/extensions` | — | API version, directory, manifests, states, redacted settings, errors |
| `POST /api/extensions` | Discriminated operation below | `{ok: true}` or `{cancelled: true}` |
| `GET /api/health` | — | `ready/degraded/stopping`, component statuses, uptime, collection age; no secrets |
| `GET /api/openapi.json` | — | This OpenAPI specification; session required |

Localized values keep their existing string or language-map representation. Actions accept short names such as `"volume.up"` or objects such as `{"type":"app.launch","target":"Music"}`. Extension argument objects remain namespaced and dynamically validated against their manifests. Optional sections use the domain defaults, not an HTTP-specific copy. `scripts` is always restored from the current trusted document before validation/save; supplying it over HTTP never changes executable commands. Full config reads necessarily contain the local console/OBS credentials and therefore require the local session.

For safe optimistic concurrency, **always echo the revision** returned by GET. A revisionless legacy document remains accepted for compatibility, but cannot provide stale-browser detection; external file fingerprint checks still apply.

The artwork preview is encoded once when the console texture changes. Reading `/api/artwork` performs no native collection or remote download. Like other API responses it is not browser-cached; the editor keeps a temporary object URL until `snapshot.media.art` changes or the media view closes.

### Extension operation bodies

```json
{"operation":"install"}
{"operation":"rescan"}
{"operation":"enable","id":"org.example.extension","trust":true,"digest":"approved-package-sha256"}
{"operation":"disable","id":"org.example.extension"}
{"operation":"restart","id":"org.example.extension"}
{"operation":"configure","id":"org.example.extension","settings":{"minutes":25}}
{"operation":"remove","id":"org.example.extension","confirm":true}
```

Install opens a native file picker. It cannot accept a browser-supplied executable, command or import path. Enabling requires explicit approval of the installed package fingerprint. Settings declared as passwords are redacted from extension catalog responses; `secret_fields_set` reports only which are populated. API 1 SDK/process transport is unchanged.

## Errors

Application errors retain `error` and add stable `code` and `request_id`; `X-Request-ID` matches the latter. Pydantic input values are not echoed.

```json
{"error":"la configuration a change depuis son ouverture; rechargez-la","code":"config_conflict","request_id":"opaque-id"}
```

| HTTP | Codes / meaning |
|---|---|
| 400 | `invalid_body`, `body_timeout`, `ambiguous_headers`; malformed/empty JSON or non-object document |
| 403 | `invalid_session`, `host_refused`, `origin_refused`; filesystem containment errors use `http_403` |
| 404 / 405 | `device_not_found`, `http_404` / `http_405`; missing paired console, unknown route or unsupported method |
| 409 | `config_conflict`, `no_config_file`, `selection_unavailable`, `permission_unavailable`, `obs_unavailable` |
| 413 | `body_too_large`, `headers_too_large` |
| 422 | `validation_failed`, `invalid_config`, `invalid_obs_config`, `invalid_permission`, `invalid_selection`, `invalid_extension`, `extension_operation_failed` |
| 500 | `config_write_failed`, `internal_error`; unexpected details/secrets are not returned |
| 503 | `stopping`, `not_ready`; Uvicorn overload is a separate parser/server-level response |

Only `403 invalid_session` should erase the browser session token. A forbidden origin does not invalidate that token. A console disconnect during publication does not undo a successful configuration commit. A client abandoning its HTTP request does not cancel an already admitted commit.

Static GET/HEAD responses support HTML, JS, CSS, SVG, PNG and WOFF2. HEAD has no body. Traversal and symlinks escaping the static root are refused. Only hashed assets get long-term cache headers; API and HTML are never immutable-cached.

## Regenerating contracts

From `agent/`:

```sh
uv run --locked python -m deck3ds.api.export ../docs/api/openapi.json
pnpm api:types
uv run --locked python -m deck3ds.api.export --check ../docs/api/openapi.json
pnpm api:check
```

No native adapter, network listener or extension process is needed. Generated TypeScript lives in `frontend/src/api/generated.ts`; `app/types.ts` aliases those contracts and keeps only visual state local. The handwritten HTTP client retains local session handling and structured errors.

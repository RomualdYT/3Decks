# Contributing to the agent

[Documentation](README.md) · [Français](CONTRIBUTING_AGENT.fr.md) · [Architecture](ARCHITECTURE.md) · [HTTP API](api/README.md) · [Extension authors](EXTENSIONS.md)

## First source launch

From a checkout, use a private configuration so the tracked demonstration stays neutral.
Install uv, Node.js 24 and pnpm 11.19.0, then from `agent/`:

```sh
uv sync --locked
pnpm install --frozen-lockfile
pnpm build
uv run --locked deck3ds --config config.local.json --init-config
uv run --locked deck3ds-ui --config config.local.json
```

Skip initialization if that file already exists. Keep passing `--config` on later
launches; the ignored local file is not automatically selected. The frontend
build is necessary when compiled assets are not already provided.

## Reproducible development

Use Python 3.12–3.14 and uv 0.10.12 or a compatible newer version. From `agent/`:

```sh
uv sync --locked
uv run --locked ruff check backend/deck3ds deck3ds tests tools
uv run --locked mypy
uv run --locked pytest --cov --cov-report=term-missing
```

The `test`, `quality` and combined `dev` dependency groups are separate. Do not add runtime tooling to the runtime dependency list. Update `pyproject.toml` and `uv.lock` together for intentional dependency changes; CI uses locked installation. Version is read from `backend/deck3ds/version.py` by the build backend.

The combined line-coverage gate is 90% for `api`, `services`, `runtime` and `desktop`, not for untouched native adapters or every individual file. Mypy is strict on those boundaries. Ruff covers the whole Python tree. Existing unittest tests run under pytest and are grouped by responsibility. A module approaching 400 lines warrants review, not automatic fragmentation.

## Frontend development with the protected proxy

Use Node 24 and pnpm 11.19.0. Stop the preceding agent before starting the development instance; create `config.local.json` as above first:

```sh
pnpm install --frozen-lockfile
uv run --locked deck3ds --config config.local.json --ui --ui-dev-origin http://127.0.0.1:4173
```

In another terminal, from `agent/`, run `pnpm dev`. Open `http://127.0.0.1:4173/?token=THE_CURRENT_UI_SESSION_TOKEN` using the token from the **newly printed agent link**, not the durable console token. Vite proxies `/api` to 38124. `strictPort` prevents it silently selecting another origin. If you change the agent UI port, update Vite's proxy as well.

`--ui-dev-origin` is repeatable, loopback-only and absent by default. It adds no permissive CORS. Never make production Host/Origin checks accept arbitrary origins to work around a dev setup issue. Tokens are session-scoped; never commit or share them.

```sh
pnpm api:check
pnpm typecheck
pnpm test:frontend
pnpm build
```

Vite writes `backend/deck3ds/api/static`. Source maps are excluded from Python distributions. PNG assets and font licenses originate in `frontend/public`; Inter font binaries come from the locked font package. No external resource is required by the built interface.

## Adding a route or operation

1. Put the operation in a focused service, with explicit dependencies and no FastAPI imports. Raise `ServiceError(status, message, code)` for expected errors. Keep secrets out of messages.
2. Add request/response structures in `api/models.py`, `catalog_models.py`, or a focused model module. For configuration, preserve the shared domain validator and raw preflight semantics; do not introduce another set of default values or reference rules.
3. Add a thin async route in the appropriate domain router. Use the typed `ApplicationServices` dependency, a stable operation ID and response model. Avoid adding native calls or runtime objects to routes.
4. Add service tests plus HTTP contract tests. Exercise invalid input, cancellation, current session/origin policy and shutdown if the operation holds resources.
5. Regenerate OpenAPI and TypeScript together, run drift checks, then use the generated frontend types. Preserve the existing error/session behavior.

A cached in-memory read should stay on the event loop. A blocking native/filesystem call belongs in the appropriate bounded pool. Do not mark an operation finished merely because its coroutine timed out. For long OS dialogs, use the owned process API rather than a shared integration shell.

## Adding an integration

Prefer an [API 1 extension](EXTENSIONS.md) for independently distributed integrations. Its SDK has no FastAPI dependency. For a built-in integration, update the shared action/feature catalogs, dispatcher and relevant platform adapter. The console continues to send allow-listed identifiers, not commands. Keep native platform behavior isolated and add simulated macOS/Windows tests.

Do not automatically install extension dependencies or execute unapproved packages. Native file selection and explicit fingerprint approval remain required. Installed Python extensions use the agent's interpreter and bundled SDK; authors must package appropriate dependencies themselves.

## Build and qualify a release

For the console, run `./build.sh` from the repository root with Docker available,
or use `make` in `3ds-app/` with local devkitPro. Output is
`3ds-app/deck3ds.3dsx`. Copy it to SD or run `python3 tools/send3ds.py` from the
root while Homebrew Launcher is ready for 3dslink. A memory transfer does not
replace the installed SD file.

Run `python3 tools/check_docs.py` from the root after documentation changes.
Keep English and French separate; see the [documentation policy](README.md).

```sh
pnpm build
uv build
uv run --locked python tools/qualify_wheel.py dist/deck3ds-0.2.0-py3-none-any.whl
```

`uv build` constructs a wheel from the source archive, checking the sdist is sufficient. `qualify_wheel.py` audits required resources and excluded personal/cache files, exports locked runtime constraints, creates a temporary virtual environment outside the repository, installs the wheel and exercises CLI, assets, HTTP, TCP and the example extension. Its smoke process cannot find Node and has no checkout PYTHONPATH.

CI builds the frontend and distribution, then tests Linux/macOS/Windows × Python 3.12/3.13/3.14, and builds the homebrew separately. Download artifacts instead of rebuilding frontend dependencies on the user's computer. A matching version tag publishes the qualified wheel, checksummed launchers and homebrew through GitHub Releases. Store identity provisioning, Store submission and deployment to a physical console remain explicit human operations.

Before release, follow the native checklist in [QUALIFICATION.md](QUALIFICATION.md), preserve the previous artifact and back up configuration plus adjacent extension data. Rollback replaces the artifact; do not reintroduce a second HTTP implementation.

The full publishing and Store-submission procedure lives in [Release procedure](PUBLIC_RELEASE.md).

CI action references: [uv setup](https://github.com/astral-sh/setup-uv), [artifact upload](https://github.com/actions/upload-artifact), [artifact download](https://github.com/actions/download-artifact).

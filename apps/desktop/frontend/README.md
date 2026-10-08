# Shared editor

React/HeroUI editor displayed by the Tauri desktop application. This directory
contains pages, settings, status, extensions, localized copy and generated API types.
The desktop entry point and onboarding live in [apps/desktop](../README.md).

## Layout

| Directory | Contents |
| --- | --- |
| `src/app/` | Editor shell and shared state types |
| `src/editor/` | Pages, templates, console preview and action controls |
| `src/settings/`, `src/status/`, `src/extensions/` | Main views |
| `src/components/`, `src/styles/`, `src/i18n/` | Shared controls, styling and English/French copy |
| `src/api/` | Typed client boundary and adapters |
| `api/openapi.json` | Contract used to generate TypeScript types |

The desktop Vite build maps `src/api/http.ts` to `apps/desktop/src/tauri-api.ts`.
Components use the shared client boundary; native OS behaviour belongs in Rust.
The standalone frontend build is a development tool, not another desktop app.

## Development checks

With Node.js 24 and pnpm 11, from this directory:

```sh
pnpm install --frozen-lockfile
pnpm api:check
pnpm typecheck
pnpm test:frontend
```

After changing the OpenAPI contract, run `pnpm api:types` and commit the generated
file. Start the actual app using the [desktop guide](../README.md#development).
See [architecture](../../../docs/ARCHITECTURE.md) and
[asset generation](../../../resources/README.md) before changing shared rendering.

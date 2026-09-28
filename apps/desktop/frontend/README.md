# Shared editor

This directory contains the React 19/HeroUI editor displayed by the Tauri application. It holds the page editor, settings, status view, translations and generated TypeScript API types. The desktop window is started from [`apps/desktop/`](../README.md), which builds this source with its Tauri command adapter and onboarding. The standalone frontend build is a developer check, not a second desktop application.

## Layout

| Directory | Contents |
|---|---|
| `src/app/` | Editor shell and shared state types |
| `src/editor/` | Pages, templates, preview and action controls |
| `src/settings/`, `src/status/`, `src/extensions/` | Main views |
| `src/components/`, `src/styles/`, `src/i18n/` | Design system, styles and FR/EN copy |
| `src/api/` | Typed editor boundary, generated types and isolated HTTP adapter |
| `api/openapi.json` | Snapshot used to generate and check editor types |

The desktop build maps `src/api/http.ts` to `apps/desktop/src/tauri-api.ts` and loads `apps/desktop/src/DesktopRoot.tsx`. Components call the shared editor boundary rather than importing Tauri directly. Keep any OS behavior in Rust; adapt the TypeScript boundary when adding a command.

## Checks

Use Node.js 24 and pnpm 11:

```sh
pnpm install --frozen-lockfile
pnpm api:check
pnpm typecheck
pnpm test:frontend
```

To run the actual application, follow the [desktop development guide](../README.md#développement). The [architecture guide](../../../docs/ARCHITECTURE.md) explains the network and native layers.

# Build and contribute

[Documentation](README.md)

## Prerequisites

- Rust stable (edition 2024 for the desktop and extension SDK).
- Node.js 24 and pnpm 11; the frontend lockfile specifies its package-manager version.
- [Tauri platform prerequisites](https://v2.tauri.app/start/prerequisites/) for the desktop.
- Docker for console packaging, or a local devkitPro toolchain.
- Python 3 for documentation and packaging tools; Focus's builder needs Python 3.9+.

From the repository root:

```sh
cd apps/desktop/frontend
pnpm install --frozen-lockfile
pnpm api:check
pnpm typecheck
pnpm test:frontend
cd ..
npm ci
npm run build
cargo test --locked --manifest-path src-tauri/Cargo.toml
npm run tauri -- dev
```

## Other checks and builds

From the repository root:

```sh
bash tools/test_console.sh
./build.sh all
python3 tools/check_docs.py
python3 examples/extensions/focus/package.py
```

The console tests use a local C compiler; `build.sh` needs Docker running.
[Quality CI](../.github/workflows/quality.yml) runs lightweight Linux checks on
pushes and pull requests: Markdown links always, frontend checks and console host
tests when their files change. Native desktop tests and package builds run for
release tags, or manually through **Quality** with `full` enabled. See the
[release process](RELEASE.md#ci-and-build-consumption) for the full CI policy.
Tests/builds do not replace runtime checks on each platform.

## Change boundaries

- OS-specific Rust calls belong in `apps/desktop/src-tauri/src/platform/`.
- Shared integrations belong in `features/`, network/session code in `transport/`,
  and lifecycle/configuration in `app/`.
- React components use the typed editor API boundary. Regenerate OpenAPI types
  with `pnpm api:types` after changing its contract.
- Update English/French text and user guides for visible behaviour changes.
- Follow [shared asset instructions](../resources/README.md) for generated images/icons.
- Keep stable page/action/contribution IDs; labels can change independently.

Only one server can bind the default UDP/TCP ports. Development overrides are
listed in the [desktop README](../apps/desktop/README.md#development-environment-variables).
See [Windows runtime checks](../apps/desktop/docs/WINDOWS_TEST_PLAN.md),
[macOS checks](../apps/desktop/docs/MACOS_TRAY_AND_SHORTCUTS_TEST.md) and
[release qualification](QUALIFICATION.md) when changing native integrations.

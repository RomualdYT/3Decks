# Build and contribute

Install Rust stable, Node.js 24, pnpm 11 and the [Tauri 2 prerequisites](https://v2.tauri.app/start/prerequisites/) for your OS. A 3DS package additionally needs Docker or devkitPro.

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

From the repository root, `bash tools/test_console.sh` runs host C tests, and `./build.sh all` builds `.3dsx` and `.cia` with the packaging container. `python3 tools/check_docs.py` validates maintained Markdown links. Quality CI performs these checks and compiles the native backend on macOS and Windows.

Two desktop servers cannot use the default UDP/TCP ports simultaneously. For a separate local test, set `DECKS_TCP_PORT` and `DECKS_DISCOVERY_PORT`; automatic 3DS discovery still targets the default port.

Keep OS-specific code in `apps/desktop/src-tauri/src/platform/`. Shared domain logic belongs in `features/`, network framing in `transport/`, and desktop lifecycle and persistence in `app/`. Update [the Windows test plan](../apps/desktop/docs/WINDOWS_TEST_PLAN.md) when changing a Windows adapter.

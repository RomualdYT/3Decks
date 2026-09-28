# Contributing

The desktop app is in [`apps/desktop/`](apps/desktop/README.md); its shared editor is in [`apps/desktop/frontend/`](apps/desktop/frontend/README.md); the 3DS client is in [`apps/console/`](apps/console/). Start with the [build guide](docs/CONTRIBUTING.md), [architecture](docs/ARCHITECTURE.md) and [Windows validation plan](apps/desktop/docs/WINDOWS_TEST_PLAN.md).

Keep platform-specific Rust adapters isolated, update user-facing documentation with behavior changes, and run the relevant frontend, Rust and C checks before a pull request. Do not commit signing keys, personal configuration or pairing data.

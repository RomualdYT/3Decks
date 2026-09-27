# Contributing

The supported desktop app is in [`desktop/`](desktop/README.md); its shared editor is in [`frontend/`](frontend/); the 3DS client is in [`3ds-app/`](3ds-app/). Start with the [build guide](docs/CONTRIBUTING.md), [architecture](docs/ARCHITECTURE.md) and [Windows validation plan](desktop/docs/WINDOWS_TEST_PLAN.md). The Python implementation is archived under [`legacy/python-agent/`](legacy/python-agent/README.md).

Keep platform-specific Rust adapters isolated, update user-facing documentation with behavior changes, and run the relevant frontend, Rust and C checks before a pull request. Do not commit signing keys, personal configuration or pairing data.

# Rust desktop architecture

`lib.rs` is the Tauri composition root: it registers IPC commands, creates the
shared state, starts the network task and owns the tray/window lifecycle.
`main.rs` only starts the app.

| Directory | Responsibility | OS boundary |
| --- | --- | --- |
| `app/` | Configuration, editor API, pairing/session state and persisted onboarding progress | OS-independent, apart from discovery of the app config directory |
| `transport/` | UDP discovery, authenticated TCP sessions and 3DS binary/JSON framing | Tokio sockets; no WebView dependency |
| `features/` | OBS, telemetry, notification reader, artwork and native extension host | A feature may use an OS adapter; unsupported providers report unavailable |
| `platform/` | Action dispatch, audio facade and window enumeration | CoreAudio/AppKit in `macos/` and `audio.rs`, Windows COM/Shell/Input in `win32/`, explicit Linux stubs |

The transport runs on Tauri's Tokio runtime. Each authenticated console gets
its own task; state polling and UDP discovery are separate tasks. The WebView
only calls IPC commands. The transport never waits on the WebView.

## Adding an OS provider

Keep the editor API and 3DS protocol stable. Add the native implementation in
`platform/macos/`, `platform/win32/` or `platform/linux/`, select it with `cfg(target_os = "windows")` or
`cfg(target_os = "linux")`, then expose the capability in
`app/desktop.rs`. The UI must use those capabilities and feature availability
instead of assuming a platform is implemented. Avoid adding platform-specific
branches to `transport/protocol.rs`.

Extensions use a package-local executable selected by OS and architecture.
The author-facing Rust SDK lives in `desktop-poc/extension-sdk/`; the host
validates the package and runs the executable over bounded JSON Lines stdio.
It does not load third-party code into the Tauri process or invoke Python.

`app/onboarding.rs` writes the completed step to the Tauri config directory.
macOS permissions can close the process, so the UI saves each completed step
before opening the next one. The editor can reopen the wizard from Settings.

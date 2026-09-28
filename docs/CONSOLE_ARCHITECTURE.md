# Console architecture

[Documentation](README.md) · [Français](CONSOLE_ARCHITECTURE.fr.md) · [Wire protocol](PROTOCOL.md)

## Repository layout

The repository contains two applications: `apps/desktop/` is the Rust/Tauri app
with its React editor in `frontend/`, and `apps/console/` is the native 3DS client.
Native PC adapters belong under `apps/desktop/src-tauri/src/platform/`, including
CoreAudio. Generated build products and dependency caches are not source files.

| Console directory | Responsibility |
|---|---|
| `source/main.c` | SDK initialization, input dispatch, frame loop and shutdown |
| `source/app/` | Application state, navigation, action feedback, connection orchestration and metric history |
| `source/network/` | Nonblocking TCP, bounded framing, discovery and timeout policy |
| `source/protocol/` | JSON, wire messages, extension state decoding and bounded models |
| `source/ui/` | Screens, setup, modal controls, localization and touch geometry |
| `source/graphics/` | Drawing, text/layout cache, icons, artwork, stereo and palette |
| `source/platform/` | Monotonic clock, SD settings and sound |
| `tests/` | Host C tests and explicitly limited SDK boundary stubs |

The Makefile lists source directories explicitly and keeps tests out of the
homebrew binary. Filenames must remain unique across source directories because
devkitPro's object rules use basenames. After moving source files, use
`./build.sh rebuild` once to clear generated dependency paths.

## Ownership and maintainability

There is one main application thread. Network reads, message decoding and state
installation are sequential; no background thread mutates the model during
drawing. Large configuration and JSON arenas are static rather than placed on
the small console stack.

Setup state, input, top rendering, bottom rendering and geometry have separate
modules. The tactile interface similarly separates grid, list, status/standby,
action feedback and chrome. Internal headers expose shared geometry so hit
testing and drawing use the same rectangles. They are not extension APIs.

Protocol parsing of extension cards is separate from their renderer. Extensions
contribute bounded declarative data; third-party executable code does not run on
the console. Navigation and feedback are independently testable without GPU calls.

## Network budgets and deadlines

TCP uses the unchanged four-byte big-endian length prefix. Payloads must contain
1–65,536 bytes. A receive destination needs an additional byte for the C string
terminator; undersized destinations cause an explicit error, never truncation.

A frame iteration allows at most eight receive calls and 65,540 incoming bytes.
Complete buffered frames are consumed before another receive. A full buffer
containing a valid frame is normal. At most eight messages are decoded per frame.
Writes retain eight queue slots and each flush allows at most eight send calls;
partial writes and would-block results continue on subsequent polls. These are
work limits, not a measured frame-time guarantee.

| Event | Policy |
|---|---|
| Pending TCP connection | Eight seconds |
| Sent hello awaiting acknowledgement | Eight seconds |
| Periodic ping after handshake | Every five seconds |
| No decoded incoming traffic | Reconnect after 15 seconds |
| Failed connection attempts | 2, 4, 8, 15, then 30 seconds |
| Console resume | Reset connection and retry immediately |
| Setup connection probe | 18 seconds; a later successful reconnect updates the result |

Deadlines use system ticks, not the wall clock or animation delta. Long frames
therefore do not postpone link failure detection. The heartbeat detects silence;
valid state traffic also proves liveness, even when a pong is delayed.

Automatic discovery presents the computer's friendly name and connects to its
numeric address. Manual setup accepts a **numeric IPv4 address**, not a DNS
hostname, avoiding synchronous DNS on the rendering thread. Existing hostname
settings must be replaced through discovery or the manual field. Credentials,
ports, discovery messages and configuration formats otherwise remain unchanged.

## Text and resource budgets

Text layout caches at most 64 measured strings and 32 clipped labels, with
approximately 22 KiB of static storage. Keys include the original UTF-8 text,
scale and (for clipping) available width. Long input bypasses caching, entries
are replaced in bounded rotation, and initialization/shutdown reset the caches.
A font change must reset them too. There is no per-frame heap allocation.

Clipping preserves UTF-8 boundaries. If even an ellipsis cannot fit, it draws no
text. Parsed GPU text remains frame-local; the cache does not retain GPU pointers.
Optional artwork/font/sound failures keep their documented fallback behavior;
required text allocation and rendering initialization failures clean up and exit.
Discovery closes before the network service shuts down.

## Tests and hardware qualification

Run `bash tools/test_console.sh` from the repository root on macOS or Linux with
a C compiler. AddressSanitizer, UndefinedBehaviorSanitizer and float-cast checks
are enabled by default. `SANITIZE=0` is available for a compiler without them,
not as a substitute for the CI sanitizer run.

Tests compile production framing, transport, JSON/protocol, extension parsing,
navigation, geometry, feedback and text-layout code. Loopback tests use actual
POSIX sockets; only SDK services, time and unrelated native presentation effects
are replaced. The shell runner uses and removes a dedicated temporary directory.
The network test has a process alarm so a regression cannot hang indefinitely.

These tests do not simulate libctru SOC quirks, GPU rendering, Wi-Fi broadcast,
battery usage or physical touch accuracy. Cross-compilation must also pass, then
follow the [native qualification checklist](QUALIFICATION.md). See
[performance measurement](PERFORMANCE.md) before making speed claims.

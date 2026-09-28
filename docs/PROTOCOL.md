# Console protocol 1

[Documentation](README.md) · [Français](PROTOCOL.fr.md) · [Extension API](EXTENSIONS.md)

This is the PC–3DS transport, not the editor's HTTP API. Implementations: `apps/desktop/src-tauri/src/transport/` and `apps/console/source/protocol/protocol.c`. Version/host values in examples are illustrative.

## Transport and discovery

The agent listens for persistent TCP connections, normally `0.0.0.0:38123`. No HTTP, WebSocket or TLS is used on this channel. Use only a trusted LAN.

Before connecting, the console broadcasts to UDP **38122**:

```json
{"type":"deck3ds.discover","protocol":1,"nonce":42}
```

The agent replies to the sender:

```json
{"type":"deck3ds.agent","protocol":1,"name":"Office Mac","platform":"macos","port":38123,"version":"0.2.0","pairing_required":true,"nonce":42}
```

Use the datagram's source address, not an IP embedded in JSON. Manual address/port setup remains available when broadcasts are filtered.

## Framing

Each TCP payload has a **4-byte big-endian unsigned length**, excluding the header. Maximum payload is **65,536 bytes**; reject oversized frames instead of allocating them. Reads/writes may be fragmented.

Ordinary payloads are UTF-8 JSON objects without a newline requirement. Artwork is the binary exception described below. The console uses bounded buffers and a non-blocking send queue.

## Session

The client sends `hello`; the agent responds with `hello.ok`, then `config.snapshot` and `state.update` without another request. The client sends presses/values; the agent responds with action results and state changes. Periodic ping/pong detects a silent link. Reconnection backs off through 2, 4, 8, 15 and 30 seconds.

### Client hello

```json
{"type":"hello","protocol":1,"device":"new3dsxl","language":"en","token":"stored-credential"}
```

For pairing, use `pair_code` with the six-digit code shown locally instead of a stored credential. When pairing is required and credentials do not match, the agent returns `hello.error` with `code:"pairing_required"` and closes.

A valid code is consumed once. The response supplies a new individual credential for the console to store:

```json
{"type":"hello.ok","protocol":1,"agent":"0.2.0","host":"Office Mac","platform":"darwin","token":"new-individual-credential"}
```

`token` is included after pairing or bootstrap-token exchange, not on every normal handshake. The agent keeps only the credential's SHA-256 digest in `paired-consoles.json`. Individual revocation closes matching connections.

One absolute five-second deadline covers the entire handshake, including fragments. Admissions are capped at 16 pending and eight authenticated clients; overload can return `hello.error` with `server_busy`. Pair-code failures are limited to five per source and 30 globally per one-minute window.

## Client requests

| Type | Fields | Purpose |
|---|---|---|
| `button.press` | `id`, `page`, `button`, optional `hold` | Execute configured primary/secondary action |
| `value.set` | `id`, `target`, `value` | Set `volume` or `app_volume`; integer 0–100 |
| `audio.output.select` | `id`, `output` | Select an output advertised when `audio_output_mode` is `direct` |
| `config.request` | `id` | Request the latest resolved layout |
| `ping` | `id` | Receive a correlated `pong` |

```json
{"type":"button.press","id":7,"page":"main","button":"mic-toggle","hold":false}
{"type":"value.set","id":8,"target":"volume","value":50}
{"type":"audio.output.select","id":9,"output":"0123456789abcdef0123456789abcdef"}
{"type":"config.request","id":10}
{"type":"ping","id":11}
```

Mutation IDs must be nonnegative integers increasing across press, value and audio-selection requests within a TCP session. Duplicate/older IDs are rejected, preventing duplicate effects in that session. The counter resets with the connection; this is not cryptographic replay protection. A paused agent rejects mutations while keeping state/connection alive.

The reserved `__direct` page accepts only `audio_output.cycle`, `volume.mute_toggle`, `mic.mute_toggle`, `volume.up` and `volume.down`. Other actions resolve from configured identifiers. The dynamic editor catalog describes supported action arguments; adding an action does not extend the direct network allow-list.

## Agent responses

### Configuration snapshot

```json
{"type":"config.snapshot","revision":4,"pages":[
  {"id":"main","title":"Main","icon":"star","dashboard":"auto","layout":"grid",
   "buttons":[{"id":"mic-toggle","slot":0,"label":"Mic","icon":"mic","color":"#66CB10","toggle":"mic_muted","hold_label":"Secondary"}]}
]}
```

The full snapshot rebuilds the console layout. It contains display metadata and identifiers, **not executable paths, URLs or action commands**.

| Page field | Meaning |
|---|---|
| `id`, `title`, `icon` | Identity and tab display; localized text resolved by agent |
| `dashboard` | `auto`, `media`, `system`, `apps`, `audio`, `frame`, or `extension` |
| `layout` | `grid` (default) or `list` |
| `buttons` | Up to six grid positions, `slot` 0–5 |
| `entries` | Up to 32 ordered list items |

Button fields include `id`, `slot`, `label`, vector `icon`, `color` in `#RRGGBB`, optional `toggle` state key and `hold_label`. List items use `id`, `label`, `detail`, `icon`, `color` and `active`; presses use the same message as buttons. Limits include 12 pages, short 24-character labels and 32-character identifiers; native buffers also impose UTF-8 byte limits. Keep strings short. Generated lists may be reduced to fit the global frame budget.

### State updates

`state.update` is a patch: absent fields leave previous state unchanged. State includes volume/mute, microphone, active/open apps, media metadata/progress/art token, audio outputs, notifications, time/date and available performance values.

Audio state carries `audio_output` (active display name), `audio_output_mode` (`direct`, `host_only` or `unavailable`), `audio_output_count` (total available) and `audio_output_options` (up to 12 objects with `id`, `name` and `active`). IDs are opaque 32-character tokens for the current device identity. The console sends the selected token through `audio.output.select`; the agent resolves it against a fresh device list before changing the output. Windows reports `host_only`: its active output is shown, but the console does not offer remote selection.

Performance keys include `cpu`, `memory`, `memory_used_mb`, `memory_total_mb`, `disk`, `disk_free_mb`, `disk_total_mb`, `network_down_kbps`, `network_up_kbps`, `top_process`, `top_process_cpu`, optional `gpu` and `temperature`. Memory/storage units are MiB, network rates kilobits/second and temperature Celsius. Missing metrics are unavailable, not invented zeros. Time/date are resolved by the agent; the console can fall back to its own clock.

### Action result and pong

```json
{"type":"action.result","id":7,"ok":true,"message":"Microphone muted"}
{"type":"action.result","id":8,"ok":false,"message":"Player unavailable"}
{"type":"pong","id":10}
```

Results correlate with requests and drive pending/success/error feedback. They may also contain native navigation instructions such as opening a page, settings or panel, rather than executing those actions on the PC. See the protocol serializer for optional fields.

### Binary artwork

A normally length-prefixed payload starts with ASCII `ART0`, followed by little-endian width (2 bytes), height (2), token (4), then `width × height × 2` pixel bytes.

Width/height must both be 128. Pixels are RGB565 little-endian, swizzled in 8 × 8 Morton-order tiles, ready for native texture upload. The token identifies the cover and avoids resending identical images. `media.art` links state to the cover token.

## Extension display fields

Workers speak [stdio API 1](EXTENSIONS.md), never the console socket. Their private arguments and programs remain on the computer. Extension-backed pages use ordinary buttons/entries; dashboards resolve to `dashboard:"extension"`.

```json
{"type":"state.update","extension_panels":[
 {"page":"focus","title":"Focus","status":"ok","cards":[{"label":"Remaining","value":"24:12","detail":"Session","progress":4}]}
],"extension_buttons":[{"page":"focus","id":"start","active":true,"available":true}]}
```

When present, these arrays replace their previous contents; an empty array clears them. Limits: 12 panels, four cards per panel, 72 button states; title 64, label 24, value 40, detail 64 UTF-8 bytes. Progress is optional, 0–100. Status is `neutral`, `ok`, `warning` or `error`. The parser's bounded JSON budget is 8,192 tokens; the frame limit remains 65,536 bytes.

Older clients ignore unknown fields but need updated homebrew to render new extension dashboards. Protocol 1 does not download custom code to the console.

## Trust boundary

A network observer can see pairing traffic and bearer credentials. Monotonic IDs, rate limits and allow-lists do not secure a hostile LAN. A future encrypted protocol would require a negotiated, audited construction on both PC and 3DS; no homegrown cryptography is claimed. See [Security](SECURITY.md).

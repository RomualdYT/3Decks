# Stream chat

[Documentation](README.md) · [Français](STREAM_CHAT.fr.md)

Read Twitch chat on the 3DS top screen while keeping OBS controls on the touch
screen. OBS and chat connect independently; OBS does not need to be running to
read chat.

## Connect

1. Open **Settings → Streaming** in the macOS or Windows app.
2. Choose **Connect Twitch**. Twitch opens in your browser; confirm the displayed
   code and authorize reading chat. Connecting also enables chat.
3. Your own channel is selected if no channel was configured. To display another
   chat, enter its name, `@username` or Twitch channel URL, then save. **Use my
   channel** restores your own channel without changing your Twitch account.
4. In the editor, add the **Streaming** page template, or choose **Stream chat**
   as any page's top screen. Save the page configuration.

The connected account authorizes reading messages; the chat channel selects
which messages to display. Changing it does not follow a streamer on Twitch.

Official 3Decks builds include the public Twitch Client ID. Users only need to
connect their Twitch account; no developer registration or Client Secret is needed.

For a fork distributed as a different application, register your own **Public**
application in the [Twitch developer console](https://dev.twitch.tv/console/apps).
Override the bundled ID with `DECKS_TWITCH_CLIENT_ID` at compile time; the release
workflow reads the repository variable with that name. Users do not need to
configure a Twitch application. Legacy local overrides can be reset in settings.

## Reading

- **X:** pause/resume automatic scrolling on the console.
- **D-pad up/down while paused:** browse recent messages.
- **Y:** return to the newest messages.
- The desktop preview also has a pause/resume control.

The reader keeps the last 20 messages. Text wraps over up to two lines on the
console; long messages are shortened. Compact text fits more messages. Optional
timestamps use UTC, and command filtering hides new messages starting with `!`.
Official Twitch badges appear beside usernames, including channel-specific
subscriber and Bits badges. Up to three badges are shown per message; images
load in the background and use a bounded memory cache. Emotes are displayed
as their text names. Deleted messages and chat clears are
applied to the recent history, including while scrolling is paused.

Only new messages received after connection are available. A connected chat does
not mean the channel is live: Twitch chat can also be used while a stream is
offline. Changing channels clears the previous channel's history.

## Connection and privacy

The desktop uses Twitch's device authorization flow with the `user:read:chat`
permission and EventSub WebSocket. Credentials are stored in macOS Keychain or
Windows Credential Manager, separately from editor configuration. They are never
sent to the console. Disconnecting removes the locally stored credentials.

Messages remain in memory and are sent to paired consoles over the existing
local connection. They are not saved to disk. Network interruptions reconnect
automatically with bounded backoff; expired tokens are refreshed. Twitch may
require authorization again if access is revoked or the refresh token expires.

## Implementation

| Directory | Responsibility |
| --- | --- |
| `apps/desktop/src-tauri/src/features/stream_chat/` | Bounded message model, credential storage, Twitch OAuth/API, EventSub session and worker lifecycle |
| `apps/desktop/frontend/src/stream-chat/` | Typed desktop controls, localized settings, preview and polling hook |
| `apps/desktop/src-tauri/src/transport/stream_chat.rs` | Coalesce console delivery to at most four history patches per second, independently of telemetry |
| `apps/console/source/protocol/stream_chat.c` | Bounded parsing of the secret-free state snapshot |
| `apps/console/source/ui/ui_top_chat.c` | Native reader, cached text wrapping and history navigation |

YouTube and message sending are not implemented.

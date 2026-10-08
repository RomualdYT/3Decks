# Use 3Decks

[Documentation](README.md) · [Français](USAGE.fr.md)

## First launch

The setup has five steps: welcome, features, starter pages, permissions and console pairing.

The setup assistant lets you choose features, review required permissions and
pair a console. You can finish without a console and connect it later. Progress
is saved between launches. Reopen setup from **Settings → Advanced**.

The editor language follows your saved choice, otherwise the system/browser:
French for French systems, English otherwise. Console language is independent
and starts in English. Both apps save your language choice.

Closing the editor keeps the desktop app running in the system menu/tray.
That menu can reopen the editor, pause console controls or quit the app.

## Create a page

1. In **Editor**, select **Add a page**. Choose a template and its display, then click **Add page**.
2. Set a short page name and icon, then choose **Grid** or **List**.
3. Under **Button content**, choose **My own actions** for editable buttons.
4. Select an empty button, choose an action, and fill in its required fields.
5. Set its label, icon and colour, then save with the editor's bottom bar.
6. Tap the button on the connected console.

Saving applies the configuration and sends it to connected consoles without a
restart. Unsaved edits appear in the preview first. If another editor saves a
newer revision, reload and reconcile your changes before saving again.

Drag pages or buttons to reorder them. A page's context menu provides additional
operations. Templates create ordinary editable pages; choosing one does not
activate a service or grant permissions.

## Generated buttons

Choose **Available windows** to list open computer windows, or an extension source
to display that extension's items. Generated items are controlled by their source,
not edited individually. A grid shows the first six items; use a list for up to 32.
The computer preview is interactive, not a video feed from the console.

## Page templates

New installations start with **Home**, **Music**, **Applications** and **Computer**. **Add a
page** opens a catalogue with a preview of both screens before adding a page.
Streaming, Notifications and Custom are also available.

Music offers now playing, synced lyrics and full-screen artwork as display
variants. Streaming offers Twitch chat with OBS controls, or OBS controls with
system statistics. Each variant stays editable through the page settings.
The catalogue explains which features or services still need configuring;
choosing a template does not enable them automatically. Existing configurations
are preserved when upgrading.

Setup offers two Home favorites from detected applications and a Music display
choice. Notifications are added when enabled and system access is available.
Streaming can be added from the catalogue after configuring Twitch or OBS.

## Top screen

Click the current **Top screen** choice to open the searchable chooser. Extension
screens appear separately from built-in screens.

| Screen | Content |
| --- | --- |
| Automatic | Current media when available, otherwise open applications |
| Now playing | Track, artist, artwork and playback progress |
| Synced lyrics | Timestamped lyrics, with a fallback when unavailable |
| Full-screen artwork | Large album cover |
| Open applications | Foreground/open apps |
| Audio outputs | Current audio output and volume |
| Computer status | Available CPU, memory, network and storage metrics |
| Notifications | Recent notifications when the source is enabled and available |
| Stream chat | Twitch messages configured in Settings → Streaming; see [setup](STREAM_CHAT.md) |
| Extension screen | Dashboard supplied by an enabled extension |

**Lyrics:** enable media and online lyrics in Settings, or select the lyrics
feature during setup, then choose **Synced lyrics** as the Music page’s top
screen. Online lookup is off until enabled and sends track metadata to LRCLIB. Local LRC files
can be used offline; see [lyrics details](../apps/desktop/docs/LYRICS_AND_PAGE_TEMPLATES.md).

## Actions and integrations

- **Files/folders:** use the native picker. Select the item again if it moves.
- **Applications:** use detected suggestions where available; names and paths are OS-specific.
- **Keyboard shortcuts:** use the capture control. The shortcut acts in the focused app.
- **OBS:** enable its WebSocket server, copy the host/port/password into Settings,
  enable the integration and test the connection. The built-in help explains the
  steps. Default connection: `127.0.0.1:4455`. Select the returned scene names
  when configuring scene actions.
- **Hold actions:** a grid button may have a secondary action triggered by holding it.

Enable only the features you need. Missing metrics are shown as unavailable.
The music animation is decorative rather than a measured audio spectrum.

## Console controls

| Control | Behaviour |
| --- | --- |
| Tap / hold | Primary / configured secondary action |
| Drag away before release | Cancel the touch |
| Bottom dock or L/R | Change page |
| D-pad | Move grid focus or navigate a list |
| A | Confirm focus; with no grid focus, select the first slot |
| B | Clear/back out of selection |
| X / Y in the grid | Activate slots 2 / 3 |
| Gear icon or L + SELECT | Open settings |
| SELECT alone | Request the latest layout |
| START | Exit |

Console settings cover language, connection, sound, idle delay and Decky.
Decky can be off, discreet or shown during idle. The desktop's appearance setting
is separate. Console preferences and pairing are saved in
`sdmc:/3ds/deck3ds/settings.cfg`; keep that file private.

## Extensions, updates and help

[Import and enable extensions](EXTENSIONS.md), then choose their actions, button
sources and top screens in the editor. [Focus](../examples/extensions/focus/README.md)
is a complete Pomodoro example.

When the build includes an updater key, the editor checks for updates after it
opens and also offers **Settings → Advanced → Updates → Check**. Installation
requires your click and restarts the app. Builds without a key disable the updater.

Use **Community & help** in Settings for Discord or its QR code. The console also
has a Community button in settings. See [troubleshooting](TROUBLESHOOTING.md) for
connection, permission and feature problems.

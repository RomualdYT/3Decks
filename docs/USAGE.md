# Use 3Decks

[Documentation](README.md) · [Français](USAGE.fr.md)

## Your first page

1. Open the editor from the computer's 3Decks system menu.
2. Add a page in the left sidebar and give it a short name.
3. Choose **My own actions**, then select an empty button.
4. Pick an action, such as play/pause, and complete the fields shown.
5. Choose an icon and color, then save using the bottom bar.
6. Tap the button on the connected console.

Saving installs the configuration in the running agent and sends the new layout to connected consoles. You do not need to restart. If another editor changed the configuration, reload after the explicit conflict instead of repeatedly saving over it.

## Organize the touch screen

Drag pages in the sidebar to reorder them; right-click a page for its context actions. Drag buttons to reorder their positions.

- **Grid:** six large positions in a 3 × 2 layout, available on every page.
- **List:** scrollable rows, useful for generated windows or extension content.
- **My own actions:** buttons you configure.
- **Available windows:** the agent generates items for open windows; touching one focuses it on the computer.
- **Extension source:** content supplied by an enabled extension.

Generated content is not a second editable copy of your buttons. A grid displays the first six items; use a list when you need more. The preview explains generated areas; it is an editor preview, not a video stream from the console.

## Choose the top screen

| Dashboard | Use it for |
|---|---|
| Automatic | Media when available, otherwise applications |
| Now playing | Track, artist, artwork and progress |
| Audio | Volume, audio output and music activity |
| Full-screen artwork | A large album cover |
| Applications | Foreground/open applications |
| System | Available computer performance metrics |
| Extension dashboard | Cards supplied by an enabled extension |

Metrics depend on what the OS exposes. Missing GPU or temperature data is not a zero reading. Music animation is visual feedback, not a promised real-time audio-spectrum analyzer.

## Configure actions without guessing

For **Open a file/folder**, use the native selection button. Choose an existing item on this computer; the field contains its path, not the contents of the file. Canceling the picker is harmless. A moved/deleted item must be selected again.

For **Open an application**, choose a suggested installed application when available. App lists and identifiers depend on the OS; do not copy a Mac app name into a Windows setup expecting it to work unchanged.

For **Keyboard shortcut**, focus the capture control and press the combination. Use the computer platform's modifier keys. The shortcut acts in the focused application, so test it in a safe context.

For **OBS**, enable its integration in Settings, supply the WebSocket connection settings and test the connection. Use the returned scene names when configuring buttons. Streaming/recording actions can affect a live session: test with a non-live scene first.

Hold actions are optional secondary actions. The console displays pending and temporary success/error feedback while the computer processes an action.

## Console controls

| Control | Behavior |
|---|---|
| Tap | Run the selected button/list item |
| Hold a configured grid button | Run its secondary action |
| Drag away before releasing | Cancel the touch |
| Bottom tabs or L/R | Change page |
| D-pad | Move button focus or navigate the list |
| A | Confirm focused item; without grid focus, select the first slot |
| B | Clear/back out of selection |
| X / Y in the grid | Activate slots 2 / 3 |
| L + SELECT | Open console settings |
| SELECT alone | Request the latest layout |
| START | Exit the application |

Settings are also accessible while connecting. They include language, connection setup, sound and dimming. Console settings live at `sdmc:/3ds/deck3ds/settings.cfg`; pairing information is sensitive, so do not upload it.

## Integrations and extensions

Settings lets you enable only what you need. Turning the media group off preserves its individual player/artwork choices for the next activation. Some permission changes need an agent restart. [Troubleshooting](TROUBLESHOOTING.md) covers unavailable providers.

Import extensions through the Extensions tab, review their declared access and approve their fingerprint before activation. Import alone does not execute the package. See [extension trust](SECURITY.md) before enabling community code.

# Use extensions

[Documentation](README.md) · [Français](EXTENSIONS.fr.md)

Extensions run on the computer and can provide three kinds of content:

| Contribution | Where to use it |
| --- | --- |
| Action | Add/edit a button → choose an action under Extensions |
| Button source | Page settings → Button content |
| Top-screen dashboard | Page settings → Top screen → choose the extension's screen |

These are separate choices. Adding an extension action does not automatically
select its top screen or generated buttons.

## Install and enable

1. Open **Extensions → Import** and choose a `.3deckext` file for your computer.
2. Review the author, requested access and package fingerprint.
3. Enable the package by approving its fingerprint.
4. Set any required extension settings, then select its contributions in the editor.

Import alone does not execute code. A changed package requires a new approval.
Disable stops its process; restart starts a fresh instance using saved settings.
An unavailable target, startup failure or timeout is shown on the extension card.
See [security](SECURITY.md) before enabling third-party code.

## Example: Focus

[Focus](../examples/extensions/focus/README.md) provides a Pomodoro timer with saved
progress and English/French text. Create a grid page, set **Button content → Focus
controls** and **Top screen → Focus overview**. The six timer controls appear automatically.

Build a package for your computer from the repository root:

```sh
python3 examples/extensions/focus/package.py
```

The result is under `examples/extensions/focus/dist/`. CI also builds Focus packages
on macOS, Windows and Linux and exposes them as workflow artifacts.

## Create an extension

The [Rust SDK guide](../apps/desktop/extension-sdk/README.md) describes the manifest,
stdio protocol, contribution format, limits and persistence. Start with Counter
for a minimal worker or Focus for a complete example. Custom screens use up to
four declarative information cards; arbitrary HTML or executable console code
is not supported.

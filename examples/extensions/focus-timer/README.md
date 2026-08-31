# Focus timer — extension API 1

Offline example for macOS, Windows and Linux. Python standard library only.
License: GPL-3.0-only, as the 3Decks repository.

From `agent/`:

```sh
python -m deck3ds.extensions validate ../examples/extensions/focus-timer
python -m deck3ds.extensions pack ../examples/extensions/focus-timer -o focus-timer.3deckext
```

In the UI: **Extensions → Import → Review and enable**. Then select
**Focus controls** as a page's button content and **Focus dashboard** as its top
screen. Grid and list layouts both work. Alternatively add individual actions
from the **Extensions** action category and choose their duration/session type.

The only files written are completed-session counts in the agent-provided data
directory. No application, network or account is required. Restarting or applying
settings resets the current timer; completed sessions survive. The agent must
remain running for the timer to complete. The timer is not an OS alarm.

Read [the author guide](../../../docs/EXTENSIONS.md) for the protocol and SDK.

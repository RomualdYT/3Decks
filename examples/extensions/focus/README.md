# Focus for 3Decks

[Français](README.fr.md)

A small offline Pomodoro companion: six touch controls, a live top screen and
saved daily progress. English and French are included; 3Decks chooses the language.

## Install and create your page

1. In **Extensions → Import**, choose the `.3deckext` package built for your computer.
2. Review the package and approve its fingerprint to enable **Focus**.
3. In **Editor**, add a page named **Focus** with the star icon.
4. In that page's settings, choose **Grid** for the touch screen.
5. Set **Button content → Focus controls** and **Top screen → Focus overview**.

The six buttons now appear automatically; no individual action wiring is needed.
The top screen shows the countdown, today's completed sessions, completed focus
time and the next phase. You can also assign individual Focus actions to any
custom button on another page.

## Use

| Control | Behaviour |
| --- | --- |
| Start / Pause / Resume | Starts the selected timer, pauses it, or resumes the remaining time. |
| Reset | Returns the current phase to its full duration, ready to start. Statistics are kept. |
| Skip | Prepares the next phase without crediting an unfinished focus session. |
| Focus | Selects a fresh focus timer. |
| Short break | Selects a fresh short break timer. |
| Long break | Selects a fresh long break timer and starts a new cycle when you leave it. |

Pause before selecting a different phase. Selecting the current phase leaves
its countdown intact. Selecting another phase discards unfinished time; it does
not count as a completed session.

Defaults: **25 minutes of focus**, **5 minutes of short break**, **15 minutes of
long break**, a long break after **4 completed focus sessions**, and a daily goal
of **4 sessions**. Change these under **Extensions → Focus → Settings**.
Durations, cycle length and daily goal are whole numbers.

Automatic starts are off by default. Enable either **Start breaks automatically**
or **Start focus automatically** independently. Manual controls always leave the
next timer ready to start.

## What is saved

- Current phase, remaining time, running/paused state and cycle progress.
- A running timer's absolute deadline, so sleep and app restarts do not reset it.
- Completed sessions and their full durations, grouped by local completion date.
- The latest 30 active days and the lifetime completed-session count.

When Focus resumes after downtime, at most the previously running phase is
completed. An automatic next phase starts at that moment: offline time never
creates a sequence of artificial completed sessions. Daily focus time counts
only completed work sessions, not partial or skipped ones.

Changing settings keeps a running or paused timer's original duration. Ready
timers and future phases use the new settings. Saving is atomic; a save error is
reported rather than silently discarding progress. Unreadable or unsupported
saved data is preserved and reported, never overwritten with an empty timer.

The extension only writes `focus.json` in the host-provided private data directory.
It does not contact any service or require credentials. Completion is shown on
the screens; it does not play a sound or send a system notification.

## Build an importable package

From the repository root, with Rust and Python 3.9 or newer installed:

```sh
python3 examples/extensions/focus/package.py
```

The script builds with the committed Cargo lockfile and writes a package under
`examples/extensions/focus/dist/` for the current computer. On Windows, `python`
may be the Python command. The source manifest is `extension.template.json`;
the script adds the compiled target's binary mapping to the package's
`extension.json`. Build output and packages are ignored by Git.

To choose another installed target with its required platform linker:

```sh
python3 examples/extensions/focus/package.py --target x86_64-pc-windows-msvc
```

Supported targets: macOS Apple Silicon/Intel, Windows ARM64/x64 (MSVC), Linux
ARM64/x64 (GNU). Each package contains only its compiled target. Build on the
corresponding platform or use a properly configured cross-compilation toolchain.

## Code map

| File | Responsibility |
| --- | --- |
| `src/main.rs` | SDK lifecycle, actions and durable state commits. |
| `src/timer.rs` | Countdown, transitions, cycles and bounded daily history. |
| `src/config.rs` | Typed, bounded settings. |
| `src/storage.rs` | Versioned JSON persistence and atomic replacement. |
| `src/presentation.rs` | Localised touch controls and four-card dashboard. |
| `package.py` | Native build and `.3deckext` packaging. |

Uses the [native Rust extension SDK](../../../apps/desktop/extension-sdk/README.md)
and the same GPL-3.0-or-later licence as 3Decks. No frontend changes or custom
renderer are required.

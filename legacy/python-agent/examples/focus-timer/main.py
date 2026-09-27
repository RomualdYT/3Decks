"""Cross-platform, offline example of every extension contribution type.

No timers or threads are needed: monotonic time is evaluated when polled.
Completed-session count is persisted; a restart deliberately resets the timer.
"""

import math
import time

from deck3ds.extensions.sdk import Extension, Result, Snapshot

extension = Extension()
remaining = 25 * 60.0
duration = remaining
deadline = None
mode = "focus"
completed = 0


def text(en, fr):
    return {"en": en, "fr": fr}


def update(context):
    global remaining, deadline, completed
    if deadline is not None:
        remaining = max(0, deadline - time.monotonic())
        if remaining == 0:
            deadline = None
            if mode == "focus":
                completed += 1
                context.save({"completed": completed})


@extension.initialize
def initialize(context):
    global remaining, duration, completed
    duration = remaining = context.settings["minutes"] * 60.0
    completed = context.load(default={}).get("completed", 0)


@extension.action("toggle")
def toggle(context, arguments):
    global deadline, remaining
    update(context)
    if deadline is None:
        if remaining == 0:
            remaining = duration
        deadline = time.monotonic() + remaining
    else:
        deadline = None
    return Result(message="▶" if deadline else "Ⅱ")


@extension.action("reset")
def reset(context, arguments):
    global remaining, deadline
    remaining, deadline = duration, None
    return Result(message="↺")


@extension.action("start")
def start(context, arguments):
    global remaining, duration, deadline, mode
    duration = remaining = arguments["minutes"] * 60.0
    mode = arguments["mode"]
    deadline = time.monotonic() + remaining
    return Result(message=f"{arguments['minutes']:g} min")


def entry(identifier, label, icon, action, arguments=None, active=False):
    return {
        "id": identifier,
        "label": label,
        "icon": icon,
        "color": "#66CB10",
        "active": active,
        "action": {"id": action, "arguments": arguments or {}},
    }


@extension.poll
def poll(context):
    update(context)
    seconds = math.ceil(remaining)
    running = deadline is not None
    controls = [
        entry(
            "toggle",
            text("Pause" if running else "Start", "Pause" if running else "Démarrer"),
            "pause" if running else "play",
            "toggle",
            active=running,
        ),
        entry("reset", text("Reset", "Réinitialiser"), "refresh", "reset"),
        entry(
            "focus",
            text("Focus", "Concentration"),
            "clock",
            "start",
            {"minutes": context.settings["minutes"], "mode": "focus"},
        ),
    ]
    if context.settings["show_breaks"]:
        controls.extend(
            [
                entry(
                    "short_break",
                    text("5 min break", "Pause 5 min"),
                    "clock",
                    "start",
                    {"minutes": 5, "mode": "break"},
                ),
                entry(
                    "long_break",
                    text("15 min break", "Pause 15 min"),
                    "clock",
                    "start",
                    {"minutes": 15, "mode": "break"},
                ),
            ]
        )
    return Snapshot(
        states={"running": running},
        sources={"presets": controls},
        dashboards={
            "timer": {
                "title": context.settings["title"],
                "status": "ok" if running else "neutral",
                "cards": [
                    {
                        "label": text("Remaining", "Temps restant"),
                        "value": f"{seconds // 60:02}:{seconds % 60:02}",
                        "progress": round(100 * (1 - remaining / duration)),
                    },
                    {
                        "label": text("Duration", "Durée"),
                        "value": f"{duration / 60:g} min",
                        "detail": text(
                            "Focus" if mode == "focus" else "Break",
                            "Concentration" if mode == "focus" else "Pause",
                        ),
                    },
                    {
                        "label": text("Completed", "Terminées"),
                        "value": str(completed),
                        "detail": text("Focus sessions", "Sessions de concentration"),
                    },
                    {
                        "label": text("Status", "État"),
                        "value": "▶" if running else "Ⅱ",
                        "detail": text(
                            "Running" if running else "Ready",
                            "En cours" if running else "Prêt",
                        ),
                    },
                ],
            }
        },
    )


if __name__ == "__main__":
    extension.serve()

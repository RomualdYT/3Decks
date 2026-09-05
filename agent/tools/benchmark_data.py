"""Synthetic desktop state: no installed packages, native calls or personal data."""

from pathlib import Path


def populate(agent) -> None:
    from deck3ds.extensions.manager import Installed
    from deck3ds.extensions.bridge import state_payload
    from deck3ds.platforms.base import MediaInfo, NotificationInfo, SystemSnapshot
    from deck3ds.server import _snapshot_payload

    snapshot = SystemSnapshot(
        volume=42,
        muted=False,
        mic_muted=False,
        app_volume=70,
        audio_output="Headphones",
        audio_outputs=[f"Audio output {index}" for index in range(6)],
        media=MediaInfo(
            title="Demo track",
            artist="Demo artist",
            app="Spotify",
            playing=True,
            album="Demo album",
            position=42,
            duration=240,
        ),
        notifications=[
            NotificationInfo(
                app="Demo",
                title=f"Notification {index}",
                body="Synthetic notification",
                age=index,
            )
            for index in range(4)
        ],
        active_app="Demo editor",
        apps=[f"Application {index}" for index in range(8)],
        cpu=25,
        memory=50,
        memory_used_mb=8192,
        memory_total_mb=16384,
        disk=40,
        disk_free_mb=600000,
        disk_total_mb=1000000,
        network_down_kbps=120,
        network_up_kbps=15,
    )
    for index in range(4):
        identifier = f"com.example.benchmark{index}"
        agent.extensions.items[identifier] = Installed(
            Path("synthetic-not-installed"),
            {"id": identifier, "actions": []},
            "synthetic",
            status="ready",
            snapshot={
                "dashboards": {
                    "overview": {
                        "title": {"en": "Overview", "fr": "Vue d'ensemble"},
                        "status": "ok",
                        "cards": [
                            {
                                "label": f"Metric {card}",
                                "value": "42",
                                "detail": "Cached synthetic value",
                            }
                            for card in range(4)
                        ],
                    }
                },
                "sources": {
                    "items": [
                        {
                            "id": f"item{entry}",
                            "label": {"en": f"Item {entry}", "fr": f"Élément {entry}"},
                            "detail": "Synthetic item",
                            "icon": "star",
                            "color": "#66CB10",
                            "active": False,
                            "action": {
                                "id": "select",
                                "arguments": {"private": "never expose"},
                            },
                        }
                        for entry in range(12)
                    ]
                },
            },
        )
    if hasattr(agent, "services"):
        agent.services.config.current.pages[
            0
        ].dashboard = "ext:com.example.benchmark0/overview"
    agent.config.pages[0].dashboard = "ext:com.example.benchmark0/overview"
    agent._last_payload = {
        **_snapshot_payload(snapshot),
        **state_payload(agent.extensions, agent.config),
    }
    agent._logs.extend(f"[12:00:00] Synthetic event {index}" for index in range(20))

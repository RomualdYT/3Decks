"""Read-boundary ownership without redundant copies or stale response caching."""

import copy
from pathlib import Path

import pytest

from deck3ds.extensions.manager import Installed

pytestmark = pytest.mark.asyncio


async def test_snapshot_nodes_are_copied_once_per_read(agent):
    copies = []

    class CountedList(list):
        def __deepcopy__(self, memo):
            copies.append(True)
            return CountedList(self)

    agent._last_payload = {"apps": CountedList(["Editor"])}
    response = agent.services.state.read()
    assert len(copies) == 1
    response["snapshot"]["apps"].append("Not shared")
    assert agent._last_payload["apps"] == ["Editor"]


async def test_nested_state_extension_previews_and_metadata_are_detached(agent):
    state = agent.services.state
    agent._last_payload = {
        "media": {"title": "Original", "art": "art-token"},
        "notifications": [{"title": "Message", "age": 2}],
    }
    original_snapshot = copy.deepcopy(agent._last_payload)
    state._notifications = {"access": "allowed", "details": {"provider": "fake"}}
    extension = Installed(
        Path("not-installed"),
        {"id": "com.example.test", "actions": []},
        "fake",
        status="ready",
        snapshot={
            "dashboards": {
                "main": {"title": {"en": "Original"}, "cards": [{"value": "42"}]}
            },
            "sources": {
                "items": [
                    {
                        "id": "entry",
                        "label": {"en": "Original"},
                        "action": {"private": "never expose"},
                    }
                ]
            },
        },
    )
    agent.extensions.items["com.example.test"] = extension
    original_extension = copy.deepcopy(extension.snapshot)
    response = state.read()
    response["snapshot"]["media"]["title"] = "Changed"
    response["snapshot"]["notifications"][0]["age"] = 999
    response["notifications"]["details"]["provider"] = "Changed"
    response["snapshot"]["extension_previews"]["ext:com.example.test/main"]["cards"][0][
        "value"
    ] = "0"
    entry = response["snapshot"]["extension_sources"]["ext:com.example.test/items"][0]
    assert "action" not in entry
    entry["label"]["en"] = "Changed"
    assert agent._last_payload == original_snapshot
    assert extension.snapshot == original_extension
    assert state._notifications["details"]["provider"] == "fake"


async def test_next_read_observes_live_changes_without_mutating_previous_response(
    agent,
):
    agent._last_payload = {"media": {"title": "First"}}
    first = agent.services.state.read()
    agent._last_payload["media"]["title"] = "Second"
    agent.services.config.current.features.media = False
    second = agent.services.state.read()
    assert first["snapshot"]["media"]["title"] == "First"
    assert second["snapshot"]["media"]["title"] == "Second"
    assert not second["features"]["media"]
    agent._last_payload = {"media": None}
    assert agent.services.state.read()["snapshot"]["media"] is None


async def test_structured_events_are_bounded_sanitized_and_counted(agent):
    for index in range(305):
        agent.event(
            "test.event",
            level="unexpected" if index == 304 else "info",
            index=index,
            nested={"secret": "not serialized"},
            non_finite=float("nan"),
        )

    response = agent.services.state.read()
    assert len(response["events"]) == 300
    assert response["events"][0]["fields"]["index"] == 5
    assert response["events"][-1]["level"] == "info"
    assert "nested" not in response["events"][-1]["fields"]
    assert "non_finite" not in response["events"][-1]["fields"]
    assert response["counters"]["test.event"] == 305


async def test_persistent_http_state_reads_keep_authentication_and_freshness(agent):
    from deck3ds.api.server import UiServer
    import httpx

    agent._last_payload = {"media": {"title": "First"}}
    ui = UiServer(agent.services, port=0)
    await ui.start()
    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{ui.port}") as client:
            first = await client.get(
                "/api/state", headers={"X-Deck3DS-Token": ui.token}
            )
            assert first.status_code == 200
            first_port = first.extensions["network_stream"].get_extra_info(
                "client_addr"
            )
            assert first_port is not None
            agent._last_payload["media"]["title"] = "Second"
            second = await client.get(
                "/api/state", headers={"X-Deck3DS-Token": ui.token}
            )
            assert (
                second.extensions["network_stream"].get_extra_info("client_addr")
                == first_port
            )
            assert second.json()["snapshot"]["media"]["title"] == "Second"
            assert second.headers["cache-control"] == "no-store"
            denied = await client.get("/api/state")
            assert denied.status_code == 403
            assert denied.json()["code"] == "invalid_session"
    finally:
        await ui.close()

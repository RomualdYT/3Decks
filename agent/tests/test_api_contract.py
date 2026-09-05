"""Configuration and status contracts through the authenticated ASGI interface."""
import json

import pytest

pytestmark = pytest.mark.asyncio


async def test_config_round_trip_preserves_fields_and_increments_revision(client, agent):
    before = (await client.get("/api/config")).json()["config"]
    response = await client.put("/api/config", json=before)
    assert response.status_code == 200
    after = json.loads(agent.config_path.read_text(encoding="utf-8"))
    assert after.pop("revision") == before.pop("revision") + 1
    assert after == before


async def test_saved_config_is_installed_before_response(client, agent):
    document = (await client.get("/api/config")).json()["config"]
    document["pages"][0]["title"] = "Updated page"
    response = await client.put("/api/config", json=document)
    assert response.status_code == 200
    assert agent.config.pages[0].title("en") == "Updated page"
    assert agent.dispatcher.config is agent.config
    assert agent._config_mtime == agent.config_path.stat().st_mtime


async def test_stale_revision_returns_conflict_without_writing(client, agent):
    original = agent.config_path.read_bytes()
    document = (await client.get("/api/config")).json()["config"]
    document["revision"] -= 1
    response = await client.put("/api/config", json=document)
    assert response.status_code == 409
    assert response.json()["code"] == "config_conflict"
    assert agent.config_path.read_bytes() == original


async def test_generated_windows_do_not_enter_persisted_or_http_config(client, agent):
    document = (await client.get("/api/config")).json()["config"]
    document["pages"][0].update(source="windows", buttons=[])
    response = await client.put("/api/config", json=document)
    assert response.status_code == 200
    persisted = json.loads(agent.config_path.read_text(encoding="utf-8"))
    assert persisted["pages"][0]["buttons"] == []
    assert response.json()["config"]["pages"][0]["buttons"] == []
    assert agent.config.pages[0].buttons


async def test_invalid_action_returns_structured_error_and_preserves_file(client, agent):
    original = agent.config_path.read_bytes()
    document = (await client.get("/api/config")).json()["config"]
    document["pages"][0]["buttons"][0]["action"] = "unknown.action"
    response = await client.put("/api/config", json=document)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_config"
    assert agent.config_path.read_bytes() == original


@pytest.mark.parametrize("valid", [True, False])
async def test_preflight_reports_validity_without_writing(client, agent, valid):
    original = agent.config_path.read_bytes()
    document = (await client.get("/api/config")).json()["config"]
    if not valid:
        document["pages"][0]["buttons"][0]["action"] = "unknown.action"
    response = await client.post("/api/config/validate", json=document)
    assert response.status_code == 200
    assert response.json()["valid"] is valid
    assert agent.config_path.read_bytes() == original


async def test_state_exposes_available_capabilities_and_bounded_diagnostics(client, agent):
    agent.log("test diagnostic")
    response = await client.get("/api/state")
    assert response.status_code == 200
    payload = response.json()
    assert "capabilities" in payload
    assert payload["notifications"]["provider"] == "none"
    assert payload["notifications"]["available"] is False
    assert "test diagnostic" in "\n".join(payload["logs"])
    assert payload["platform"] == agent.platform.name


async def test_public_snapshot_is_detached_from_runtime(agent):
    agent._last_payload = {"type": "state.update", "media": {"title": "Test track"}}
    snapshot = agent.last_state_payload()
    snapshot["media"]["art"] = "test-art"
    assert "art" not in agent._last_payload["media"]


async def test_diagnostic_ring_has_a_fixed_bound(agent, monkeypatch):
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
    for index in range(1000):
        agent.log(f"test event {index}")
    assert len(agent.recent_logs()) <= 300

"""Editor catalogs must describe the domain's actual capabilities and limits."""
import re

import pytest

from deck3ds import config, keys
from deck3ds.platforms.base import Capabilities
from deck3ds.services.catalog import build_schema


def test_capabilities_control_action_availability():
    actions = {item["kind"]: item for item in build_schema(Capabilities(volume=True))["actions"]}
    assert actions["volume.up"]["supported"]
    assert not actions["window.focus"]["supported"]
    assert actions["settings.open"]["supported"]
    assert actions["noop"]["supported"]


def test_obs_catalog_exposes_named_scene_and_source_arguments():
    actions = {item["kind"]: item for item in build_schema(Capabilities(), obs_enabled=True)["actions"]}
    assert actions["obs.scene.set"]["supported"]
    assert [argument["name"] for argument in actions["obs.source.toggle"]["arguments"]] == ["scene", "source"]


@pytest.mark.parametrize("item", build_schema(Capabilities())["actions"], ids=lambda item: item["kind"])
def test_every_action_has_valid_bilingual_presentation(item):
    assert item["category"] in {"essential", "audio", "media", "apps", "obs", "navigation", "advanced"}
    assert item["icon"] in config.ICONS
    assert re.fullmatch(r"#[0-9A-F]{6}", item["color"])
    for language in ("en", "fr"):
        assert item["title"][language]
        assert item["description"][language]


def test_limits_and_defaults_match_domain_models():
    schema = build_schema(Capabilities())
    limits, defaults = schema["limits"], schema["defaults"]
    assert limits["buttons_per_page"] == config.MAX_BUTTONS_PER_PAGE
    assert limits["pages"] == config.MAX_PAGES
    for key, expected in (
        ("port", config.PORT_RANGE), ("poll_interval", config.POLL_INTERVAL_RANGE),
        ("volume_step", config.VOLUME_STEP_RANGE), ("obs_timeout", config.OBS_TIMEOUT_RANGE),
    ):
        assert tuple(limits[key]) == expected
    reference, obs = config.Config(), config.ObsConfig()
    for key in ("host", "port", "volume_step"):
        assert defaults[key] == getattr(reference, key)
    assert defaults["obs_host"] == obs.host
    assert defaults["obs_port"] == obs.port


def test_keyboard_catalog_round_trips_through_the_parser():
    schema = build_schema(Capabilities(hotkey=True))
    catalog = schema["keys"]
    assert catalog == keys.catalog()
    for entry in catalog["keys"]:
        assert entry["group"] in catalog["groups"]
        assert entry["label_en"] and entry["label_fr"]
        keys.parse_hotkey(entry["name"])
    hotkey = next(item for item in schema["actions"] if item["kind"] == "hotkey")
    assert hotkey["arguments"][0]["type"] == "hotkey"

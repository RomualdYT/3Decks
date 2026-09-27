"""Isolated test runtime: temporary configuration, fake OS and bounded cleanup."""

import asyncio

import httpx
import pytest_asyncio

from deck3ds.api.app import create_app
from deck3ds.api.security import HttpSettings
from deck3ds.config import load, parse, save
from deck3ds.runtime.agent import AgentRuntime
from deck3ds.transports.parts import Options
from .fixtures import FakePlatform, minimal_config


@pytest_asyncio.fixture
async def agent(tmp_path):
    path = tmp_path / "config.json"
    save(parse(minimal_config()), path)
    runtime = AgentRuntime(load(path), FakePlatform(), Options(config_path=path))
    try:
        yield runtime
    finally:
        await asyncio.wait_for(runtime.close(), 5)


@pytest_asyncio.fixture
async def client(agent):
    app = create_app(agent.services, HttpSettings(token="session"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1",
        headers={"X-Deck3DS-Token": "session"},
    ) as client:
        yield client

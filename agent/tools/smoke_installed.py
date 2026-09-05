"""Run with the wheel's Python, outside the checkout; no dev dependencies needed."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from deck3ds import config, protocol
from deck3ds.configuration.location import initialize
from deck3ds.platforms.base import Platform
from deck3ds.runtime.agent import AgentRuntime
from deck3ds.transports.parts import Options


async def get(port: int, path: str, token: str = "") -> tuple[int, bytes]:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(
        (
            f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nX-Deck3DS-Token: {token}\r\nConnection: close\r\n\r\n"
        ).encode()
    )
    await writer.drain()
    response = await asyncio.wait_for(reader.read(), 2)
    writer.close()
    await writer.wait_closed()
    head, _, body = response.partition(b"\r\n\r\n")
    return int(head.split()[1]), body


async def exercise(root: Path, example: Path | None) -> None:
    path = root / "config.json"
    initialize(path)
    loaded = config.load(path)
    assert loaded.token
    loaded.host, loaded.port = "127.0.0.1", 0
    platform = Platform()
    platform.name = sys.platform
    agent = AgentRuntime(loaded, platform, Options(config_path=path, ui_port=0))

    async def no_discovery() -> None:
        pass  # Do not interfere with the user's real discovery listener.

    agent._start_discovery = no_discovery
    agent.log = lambda _: None
    if example:
        archive = root / "example.zip"
        with zipfile.ZipFile(archive, "w") as package:
            for source in sorted(example.rglob("*")):
                if source.is_file() and "__pycache__" not in source.parts:
                    package.write(source, source.relative_to(example))
        identifier = await agent.extension_pool.run(agent.extensions.install, archive)
        await agent.extension_pool.run(
            agent.extensions.enable,
            identifier,
            True,
            agent.extensions.items[identifier].digest,
        )
        result = await agent.extension_actions_pool.run(
            agent.extensions.execute,
            f"ext:{identifier}/start",
            {"minutes": 1, "mode": "focus"},
        )
        assert result["ok"]
    task = asyncio.create_task(agent.start())
    try:
        for _ in range(300):
            if task.done():
                await task
            if agent._ui and agent._ui.running:
                break
            await asyncio.sleep(0.01)
        assert agent._ui and agent._ui.running
        status, html = await get(agent._ui.port, "/")
        assert status == 200 and b"<html" in html
        for asset in re.findall(rb'(?:src|href)="(/[^"]+)"', html):
            assert (await get(agent._ui.port, asset.decode()))[0] == 200
        static = Path(sys.modules["deck3ds.api.server"].__file__).with_name("static")
        assert list(static.rglob("*.png"))
        assert list(static.rglob("*.woff2"))
        for asset in [*static.glob("*.png"), *static.rglob("*.woff2")]:
            assert (
                await get(agent._ui.port, "/" + asset.relative_to(static).as_posix())
            )[0] == 200
        for route in (
            "config",
            "schema",
            "state",
            "health",
            "extensions",
            "openapi.json",
        ):
            status, body = await get(agent._ui.port, "/api/" + route, agent._ui.token)
            assert status == 200, route
            assert isinstance(json.loads(body), dict)
        tcp = agent._server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", tcp)
        writer.write(
            protocol.encode(
                {
                    "type": "hello",
                    "protocol": 1,
                    "device": "smoke",
                    "language": "fr",
                    "token": loaded.token,
                }
            )
        )
        await writer.drain()
        frames = protocol.FrameReader()
        received = []
        while "config.snapshot" not in [item["type"] for item in received]:
            frames.feed(await asyncio.wait_for(reader.read(65536), 2))
            received.extend(frames)
        assert (
            next(item for item in received if item["type"] == "config.snapshot")[
                "pages"
            ][0]["title"]
            == "Principal"
        )
        writer.close()
        await writer.wait_closed()
    finally:
        agent.request_stop()
        await asyncio.wait_for(task, 5)
    assert agent._closed and not agent.clients and not agent._client_tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", type=Path)
    args = parser.parse_args()
    assert shutil.which("node") is None, "Qualify in a Node-free PATH"
    with tempfile.TemporaryDirectory(prefix="3decks-installed-") as directory:
        root = Path(directory)
        for flags in (
            ("--version",),
            ("--config", str(root / "cli.json"), "--init-config"),
            ("--config", str(root / "cli.json"), "--check"),
        ):
            subprocess.run(
                [sys.executable, "-m", "deck3ds", *flags],
                cwd=root,
                check=True,
                capture_output=True,
            )
        asyncio.run(exercise(root, args.example.resolve() if args.example else None))
    print("Installed wheel: CLI, static assets, API, TCP and example extension OK")


if __name__ == "__main__":
    main()

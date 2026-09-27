"""Desktop host contracts without starting a real Cocoa or Win32 menu loop."""

from __future__ import annotations

import asyncio
import io
import plistlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from deck3ds.desktop import system
from deck3ds.desktop.application import (
    DesktopController,
    DesktopOptions,
    _launch_detached,
    run_desktop,
)
from deck3ds.desktop.autostart import (
    MacAutoStart,
    UnsupportedAutoStart,
    WindowsAutoStart,
)
from deck3ds.desktop.logging import MAX_LOG_SIZE, configure_desktop_logging
from deck3ds.desktop.instance import InstanceLock
from deck3ds.desktop.models import DesktopSnapshot, LaunchSpec
from deck3ds.desktop.translations import preferred_language, translate


class FakeAutoStart:
    supported = True

    def __init__(self) -> None:
        self.value = False

    def enabled(self) -> bool:
        return self.value

    def set_enabled(self, enabled: bool) -> None:
        self.value = enabled


class FakeTray:
    def __init__(self) -> None:
        self.snapshots: list[DesktopSnapshot] = []
        self.notifications: list[tuple[str, str]] = []
        self.stopped = False

    def run(self, setup) -> None:
        setup()

    def stop(self) -> None:
        self.stopped = True

    def refresh(self, snapshot: DesktopSnapshot) -> None:
        self.snapshots.append(snapshot)

    def notify(self, title: str, message: str) -> None:
        self.notifications.append((title, message))


def launch_spec(tmp_path: Path) -> LaunchSpec:
    return LaunchSpec(
        executable=tmp_path / "pythonw",
        arguments=("-m", "deck3ds", "--background"),
        working_directory=tmp_path,
    )


def test_macos_autostart_is_atomic_and_reversible(tmp_path):
    target = tmp_path / "LaunchAgents/3Decks.plist"
    spec = launch_spec(tmp_path)
    autostart = MacAutoStart(spec, target)
    assert not autostart.enabled()
    autostart.set_enabled(True)
    document = plistlib.loads(target.read_bytes())
    assert document["ProgramArguments"] == spec.command()
    assert document["RunAtLoad"] is True
    assert not list(target.parent.glob(".3Decks.plist.*"))
    autostart.set_enabled(False)
    assert not target.exists()


def test_windows_autostart_uses_a_shortcut_without_shell_interpolation(tmp_path):
    target = tmp_path / "Startup/3Decks.lnk"
    calls = []

    def runner(command, **options):
        calls.append((command, options))
        target.touch()
        return SimpleNamespace(returncode=0)

    spec = launch_spec(tmp_path)
    autostart = WindowsAutoStart(spec, target, runner)
    autostart.set_enabled(True)
    assert autostart.enabled()
    assert calls[0][0][0] == "powershell.exe"
    assert calls[0][1]["env"]["DECK3DS_TARGET"] == str(spec.executable)
    assert calls[0][1]["env"]["DECK3DS_ARGUMENTS"]
    autostart.set_enabled(False)
    assert not target.exists()


def test_unsupported_autostart_is_explicit():
    autostart = UnsupportedAutoStart()
    assert not autostart.supported
    assert not autostart.enabled()
    with pytest.raises(OSError):
        autostart.set_enabled(True)


def test_single_instance_handoff_is_private_and_validated(tmp_path):
    first = InstanceLock("config", tmp_path)
    second = InstanceLock("config", tmp_path)
    assert first.acquire()
    assert not second.acquire()
    first.publish_url("http://127.0.0.1:38124/?token=secret")
    assert second.existing_url() == "http://127.0.0.1:38124/?token=secret"
    first.state_path.write_text(
        '{"url":"https://evil.example/?token=x"}', encoding="utf-8"
    )
    assert second.existing_url() == ""
    first.release()
    assert second.acquire()
    second.release()


def test_translations_follow_override_and_pluralisation(monkeypatch):
    monkeypatch.setenv("DECK3DS_LOCALE", "fr-FR")
    assert preferred_language() == "fr"
    assert (
        translate("fr", "ready_many", count=3) == "Agent actif · 3 consoles connectées"
    )
    assert translate("en", "tooltip_one") == "3Decks — 1 console connected"


def test_gui_logging_rotates_and_keeps_console_output(tmp_path):
    target = tmp_path / "agent.log"
    target.write_bytes(b"x" * (MAX_LOG_SIZE + 1))
    output, errors = io.StringIO(), io.StringIO()
    with patch.object(sys, "stdout", output), patch.object(sys, "stderr", errors):
        assert configure_desktop_logging(target) == target
        print("desktop ready")
        print("warning", file=sys.stderr)
        sys.stdout.flush()
        sys.stderr.flush()
    assert target.with_suffix(".log.1").exists()
    assert "desktop ready" in target.read_text(encoding="utf-8")
    assert output.getvalue() == "desktop ready\n"
    assert errors.getvalue() == "warning\n"


@pytest.mark.asyncio
async def test_controller_applies_pause_quick_settings_and_autostart(agent, tmp_path):
    options = DesktopOptions(launch_spec(tmp_path), tmp_path / "agent.log", False, "fr")
    autostart = FakeAutoStart()
    controller = DesktopController(agent, options, autostart)
    tray = FakeTray()
    controller.attach(tray)
    controller._loop = asyncio.get_running_loop()
    await controller._capture()

    controller.pause(60)
    for _ in range(100):
        if agent.controls_paused:
            break
        await asyncio.sleep(0.005)
    assert agent.controls_paused
    assert controller.snapshot().paused

    controller.resume()
    for _ in range(100):
        if not agent.controls_paused:
            break
        await asyncio.sleep(0.005)
    assert not agent.controls_paused

    await agent.services.config.update_runtime_settings(features={"spotify": False, "apple_music": True, "media_artwork": True})
    controller.set_feature("media", False)
    for _ in range(200):
        if agent.config.features.media is False:
            break
        await asyncio.sleep(0.005)
    assert not agent.config.features.media
    assert agent.config.features.media_artwork
    assert agent.config.features.apple_music
    assert not agent.config.features.spotify
    controller.set_feature("media", True)
    for _ in range(200):
        if agent.config.features.media:
            break
        await asyncio.sleep(0.005)
    assert agent.config.features.media
    assert agent.config.features.apple_music
    assert not agent.config.features.spotify

    controller.set_obs(True)
    for _ in range(200):
        if agent.config.obs.enabled:
            break
        await asyncio.sleep(0.005)
    assert agent.config.obs.enabled

    controller.toggle_autostart()
    for _ in range(100):
        if controller.snapshot().autostart:
            break
        await asyncio.sleep(0.005)
    assert autostart.enabled()
    assert tray.snapshots


@pytest.mark.asyncio
async def test_paused_runtime_rejects_console_actions_with_human_message(agent):
    client = SimpleNamespace(
        id=7,
        language="fr",
        last_action_id=-1,
        send=AsyncMock(return_value=True),
    )
    agent.pause_controls(None)
    await agent.commands._handle_button(
        client,
        {"type": "button.press", "id": 1, "page": "main", "button": "b1"},
    )
    payload = client.send.await_args.args[0]
    assert payload["ok"] is False
    assert "barre des menus" in payload["message"]
    assert agent.platform.calls == []


def test_controller_desktop_actions_are_non_blocking(agent, tmp_path):
    controller = DesktopController(
        agent,
        DesktopOptions(launch_spec(tmp_path), tmp_path / "agent.log", False, "en"),
        FakeAutoStart(),
    )
    tray = FakeTray()
    controller.attach(tray)
    controller._ui_url = "http://127.0.0.1:38124/?token=secret"
    with (
        patch.object(system, "open_url") as open_url,
        patch.object(system, "copy_text") as copy_text,
        patch.object(system, "open_path") as open_path,
    ):
        controller.open_ui("status")
        controller.copy_address()
        controller.open_logs()
        for _ in range(100):
            if open_url.called and copy_text.called and open_path.called:
                break
            import time

            time.sleep(0.005)
    open_url.assert_called_with("http://127.0.0.1:38124/?token=secret#status")
    copy_text.assert_called_once()
    open_path.assert_called_once_with(tmp_path / "agent.log")


def test_detached_restart_uses_exact_launch_spec(tmp_path):
    spec = launch_spec(tmp_path)
    with patch("deck3ds.desktop.application.subprocess.Popen") as popen:
        _launch_detached(spec)
    assert popen.call_args.args[0] == spec.command()
    assert popen.call_args.kwargs["cwd"] == tmp_path


def test_second_desktop_launch_opens_existing_ui_and_closes_unused_runtime(tmp_path):
    runtime = SimpleNamespace(config_path=tmp_path / "config.json", close=AsyncMock())
    instance = Mock()
    instance.acquire.return_value = False
    instance.existing_url.return_value = "http://127.0.0.1:38124/?token=secret"
    options = DesktopOptions(launch_spec(tmp_path), tmp_path / "agent.log")

    with (
        patch.object(InstanceLock, "for_config", return_value=instance),
        patch.object(system, "open_url") as open_url,
    ):
        assert run_desktop(runtime, options) == 0

    open_url.assert_called_once_with("http://127.0.0.1:38124/?token=secret")
    runtime.close.assert_awaited_once()


def test_desktop_setup_failure_releases_runtime_and_instance(tmp_path):
    from deck3ds.feature_catalog import FEATURE_SPECS

    features = SimpleNamespace(**{name: True for name in FEATURE_SPECS})
    runtime = SimpleNamespace(
        config_path=tmp_path / "config.json",
        config=SimpleNamespace(features=features, obs=SimpleNamespace(enabled=False)),
        close=AsyncMock(),
    )
    instance = Mock()
    instance.acquire.return_value = True
    options = DesktopOptions(launch_spec(tmp_path), tmp_path / "agent.log")

    with (
        patch.object(InstanceLock, "for_config", return_value=instance),
        patch(
            "deck3ds.desktop.application.create_autostart", return_value=FakeAutoStart()
        ),
        patch(
            "deck3ds.desktop.tray.PystrayTray",
            side_effect=RuntimeError("GUI unavailable"),
        ),
        pytest.raises(RuntimeError, match="GUI unavailable"),
    ):
        run_desktop(runtime, options)

    runtime.close.assert_awaited_once()
    instance.release.assert_called_once()


class FakeMenu(tuple):
    SEPARATOR = object()

    def __new__(cls, *items):
        return tuple.__new__(cls, items)


class FakeMenuItem:
    def __init__(self, text, action, **options):
        self.text, self.action, self.options = text, action, options


class FakeIcon:
    HAS_MENU = True

    def __init__(self, name, icon, title, menu):
        self.name, self.icon, self.title, self.menu = name, icon, title, menu
        self.updated = 0
        self.notifications = []
        self.stopped = False

    def run(self, setup):
        setup(self)

    def stop(self):
        self.stopped = True

    def update_menu(self):
        self.updated += 1

    def notify(self, message, title):
        self.notifications.append((title, message))


class FakeActions:
    def __init__(self) -> None:
        self.value = DesktopSnapshot(features={"media": True})

    def snapshot(self):
        return self.value

    def __getattr__(self, _name):
        return Mock()


def test_tray_renders_distinct_states_and_dynamic_copy(monkeypatch):
    fake_module = SimpleNamespace(Menu=FakeMenu, MenuItem=FakeMenuItem, Icon=FakeIcon)
    monkeypatch.setitem(sys.modules, "pystray", fake_module)
    from deck3ds.desktop.tray import PystrayTray

    actions = FakeActions()
    tray = PystrayTray(actions, "fr")
    connected = DesktopSnapshot(phase="ready", client_count=2, features={"media": True})
    tray.refresh(connected)
    assert tray._status_text(None) == "Agent actif · 2 consoles connectées"
    assert tray._tooltip(connected) == "3Decks — 2 consoles connectées"
    assert tray._icon.icon.getbbox() is not None
    assert tray._icon.updated == 1
    from dataclasses import replace

    paused = replace(connected, paused=True, pause_remaining=60)
    tray.refresh(paused)
    updates = tray._icon.updated
    tray.refresh(replace(paused, pause_remaining=59))
    assert tray._icon.updated == updates
    tray.refresh(connected)
    assert tray._icon.updated == updates + 1
    tray.notify("3Decks", "Prêt")
    assert tray._icon.notifications == [("3Decks", "Prêt")]
    tray.run(lambda: None)
    assert tray._icon.visible


def test_macos_tray_mutations_are_dispatched_to_main_queue(monkeypatch):
    fake_module = SimpleNamespace(Menu=FakeMenu, MenuItem=FakeMenuItem, Icon=FakeIcon)
    scheduled = []
    app_helper = SimpleNamespace(
        callAfter=lambda operation: scheduled.append(operation)
    )
    monkeypatch.setitem(sys.modules, "pystray", fake_module)
    monkeypatch.setitem(
        sys.modules, "PyObjCTools", SimpleNamespace(AppHelper=app_helper)
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    from deck3ds.desktop.tray import PystrayTray

    tray = PystrayTray(FakeActions(), "en")
    snapshot = DesktopSnapshot(phase="ready", client_count=1)

    worker = __import__("threading").Thread(target=lambda: tray.refresh(snapshot))
    worker.start()
    worker.join()
    assert tray._icon.updated == 0
    assert len(scheduled) == 1
    scheduled.pop()()
    assert tray._icon.updated == 1

    worker = __import__("threading").Thread(target=tray.stop)
    worker.start()
    worker.join()
    assert not tray._icon.stopped
    scheduled.pop()()
    assert tray._icon.stopped

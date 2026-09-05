import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from deck3ds import __main__ as cli
from deck3ds.config import load, Config
from deck3ds.configuration import location
from deck3ds.runtime.factory import create_runtime
from deck3ds.transports.parts import Options
from .fixtures import FakePlatform


def test_help_uses_public_product_name(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["--help"])
    assert error.value.code == 0
    assert "Agent PC pour 3Decks" in capsys.readouterr().out


@pytest.mark.parametrize("stopped, expected", [(True, 0), (False, 1)])
def test_stop_uses_instance_control_without_loading_configuration(tmp_path, stopped, expected):
    from deck3ds.desktop.instance import InstanceLock

    with patch.object(InstanceLock, "request_stop", return_value=stopped) as stop:
        assert cli.main(["--config", str(tmp_path / "missing.json"), "--stop"]) == expected
    stop.assert_called_once_with()


def test_initialize_is_neutral_private_and_never_overwrites(tmp_path):
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    assert cli.main(["--config", str(first), "--init-config"]) == 0
    assert cli.main(["--config", str(second), "--init-config"]) == 0
    assert load(first).token != load(second).token
    assert len(load(first).token) >= 32
    assert load(first).scripts == {}
    assert load(first).obs.password == ""
    original = first.read_bytes()
    assert cli.main(["--config", str(first), "--init-config"]) == 1
    assert first.read_bytes() == original
    assert cli.main(["--config", str(first), "--check"]) == 0
    assert cli.main(["--config", str(tmp_path / "missing"), "--check"]) == 1
    assert cli.main(["--config", str(tmp_path / "missing")]) == 1


def test_init_if_missing_continues_and_preserves_existing_config(tmp_path):
    path = tmp_path / "config.json"
    arguments = ["--config", str(path), "--init-if-missing", "--check"]
    assert cli.main(arguments) == 0
    original = path.read_bytes()
    assert cli.main(arguments) == 0
    assert path.read_bytes() == original

    path.write_text("{invalid", encoding="utf-8")
    assert cli.main(arguments) == 1
    assert path.read_text(encoding="utf-8") == "{invalid"


def test_gui_entry_adds_safe_first_run_and_ui_flags():
    with patch.object(cli.sys, "argv", ["deck3ds-ui", "--verbose"]), patch.object(
        cli, "main", return_value=7
    ) as main:
        assert cli.ui_main() == 7
    main.assert_called_once_with(
        ["--init-if-missing", "--ui", "--desktop", "--verbose"]
    )


def test_default_location_preserves_source_checkout_and_installed_user_directory(
    tmp_path,
):
    source = tmp_path / "source"
    (source / "frontend").mkdir(parents=True)
    source_config = source / "config.json"
    source_config.write_text("{}", encoding="utf-8")
    with (
        patch.object(
            location,
            "__file__",
            str(source / "backend" / "deck3ds" / "configuration" / "location.py"),
        ),
        patch.object(location, "user_config_path", return_value=tmp_path / "user"),
    ):
        assert location.default_config_path() == source_config
        source_config.unlink()
        assert location.default_config_path() == tmp_path / "user" / "config.json"


def test_init_writing_failure_removes_only_new_partial_file(tmp_path):
    path = tmp_path / "new.json"
    with patch(
        "deck3ds.configuration.location.os.fsync", side_effect=OSError("full disk")
    ):
        with pytest.raises(OSError):
            location.initialize(path)
    assert not path.exists()


def test_cli_rejects_nonlocal_development_origin():
    with pytest.raises(SystemExit) as error:
        cli.main(["--ui-dev-origin", "https://evil.example:4173"])
    assert error.value.code == 2


def test_failed_runtime_construction_closes_native_platform():
    platform = FakePlatform()
    platform.close = Mock()
    with (
        patch("deck3ds.runtime.factory.build_platform", return_value=platform),
        patch(
            "deck3ds.runtime.factory.AgentRuntime",
            side_effect=RuntimeError("construction failed"),
        ),
    ):
        with pytest.raises(RuntimeError):
            create_runtime(Config(), Options())
    platform.close.assert_called_once()


@pytest.mark.parametrize("operating_system", ["darwin", "win32", "cygwin", "linux"])
def test_platform_factory_selects_only_the_expected_adapter(operating_system):
    from deck3ds.runtime import factory

    features = Config().features
    with (
        patch.object(
            factory, "sys", SimpleNamespace(platform=operating_system, stderr=None)
        ),
        patch("deck3ds.platforms.macos.MacPlatform") as mac,
        patch("deck3ds.platforms.windows.WindowsPlatform") as windows,
    ):
        platform = factory.build_platform(features)
    if operating_system == "darwin":
        mac.assert_called_once_with(features)
        windows.assert_not_called()
        assert platform is mac.return_value
    elif operating_system in ("win32", "cygwin"):
        windows.assert_called_once_with(features)
        mac.assert_not_called()
        assert platform is windows.return_value
    else:
        mac.assert_not_called()
        windows.assert_not_called()
        assert type(platform) is factory.Platform


def test_probe_closes_adapter_even_on_snapshot_failure():
    platform = FakePlatform()
    platform.snapshot = Mock(side_effect=RuntimeError("snapshot failed"))
    platform.close = Mock()
    with patch.object(cli, "build_platform", return_value=platform):
        with pytest.raises(RuntimeError):
            cli.command_probe()
    platform.close.assert_called_once()


def test_openapi_export_cli_check_and_stdout(tmp_path, capsys):
    from deck3ds.api import export

    target = tmp_path / "openapi.json"
    for arguments, expected in [([str(target)], 0), ([str(target), "--check"], 0)]:
        with patch("sys.argv", ["export", *arguments]):
            assert export.main() == expected
    target.write_text("{}", encoding="utf-8")
    with patch("sys.argv", ["export", str(target), "--check"]):
        assert export.main() == 1
    with patch("sys.argv", ["export"]):
        assert export.main() == 0
    assert json.loads(capsys.readouterr().out)["openapi"]
    with patch("sys.argv", ["export", "--check"]), pytest.raises(SystemExit):
        export.main()

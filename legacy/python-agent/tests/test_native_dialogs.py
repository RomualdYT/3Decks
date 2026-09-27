"""Real child process ownership without ever opening a system dialog."""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from deck3ds.platforms.dialogs import DialogProcess


def test_dialog_success_failure_and_timeout():
    dialog = DialogProcess()
    assert dialog.run([sys.executable, "-c", "print('selected')"]).strip() == "selected"
    with pytest.raises(RuntimeError, match="failed"):
        dialog.run([sys.executable, "-c", "raise SystemExit(1)"])
    with pytest.raises(RuntimeError, match="timed out"):
        dialog.run([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.01)
    assert dialog._process is None
    dialog.close()
    with pytest.raises(RuntimeError, match="stopping"):
        dialog.run([sys.executable, "-c", "print('never')"])


def test_shutdown_terminates_owned_process_and_rejects_second_dialog():
    dialog = DialogProcess()
    with ThreadPoolExecutor(1) as pool:
        running = pool.submit(
            dialog.run, [sys.executable, "-c", "import time; time.sleep(10)"]
        )
        deadline = time.monotonic() + 2
        while dialog._process is None and time.monotonic() < deadline:
            time.sleep(0.001)
        process = dialog._process
        try:
            assert process is not None
            with pytest.raises(RuntimeError, match="already open"):
                dialog.run([sys.executable, "-c", "print('never')"])
        finally:
            dialog.close()
        with pytest.raises(RuntimeError):
            running.result(timeout=2)
        assert process.poll() is not None


def test_shutdown_escalates_to_kill_when_terminate_times_out():
    dialog = DialogProcess()
    process = dialog._process = Mock()
    process.wait.side_effect = [subprocess.TimeoutExpired("fake", 1), 0]
    dialog.close()
    process.kill.assert_called_once()
    dialog._process = Mock()
    dialog._process.terminate.side_effect = OSError("already exited")
    dialog.close()


def test_windows_selection_is_independent_from_shared_powershell():
    from deck3ds.platforms.windows import WindowsPlatform

    platform = WindowsPlatform.__new__(WindowsPlatform)
    platform.run_dialog = Mock(return_value="C:\\Documents\\chosen.txt")
    platform._ps = Mock(side_effect=AssertionError("must not share the session"))
    assert platform.choose_path("file") == "C:\\Documents\\chosen.txt"
    command = platform.run_dialog.call_args.args[0]
    assert "-Sta" in command
    platform._ps.assert_not_called()

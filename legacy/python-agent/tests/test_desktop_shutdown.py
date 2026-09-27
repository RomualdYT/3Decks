"""Real lock handoff, timed shutdown and continuous log rotation."""
import os
import threading
import time
from unittest.mock import patch
from unittest.mock import Mock

from deck3ds.desktop.application import DesktopController
from deck3ds.desktop.instance import InstanceLock
from deck3ds.desktop.logging import RotatingLog


def test_background_admission_is_bounded_and_released_after_failure():
    controller = DesktopController.__new__(DesktopController)
    controller._background_slots = threading.BoundedSemaphore(4)
    controller._notify_error = Mock()
    operation = Mock(side_effect=RuntimeError("test operation"))
    with patch("deck3ds.desktop.application.threading.Thread") as thread:
        for _ in range(5):
            controller._background(operation)
        assert thread.call_count == 4
        targets = [call.kwargs["target"] for call in thread.call_args_list]
        for target in targets:
            target()
        assert controller._notify_error.call_count == 4
        thread.return_value.start.side_effect = RuntimeError("thread unavailable")
        controller._background(operation)
        assert controller._notify_error.call_count == 5
        for _ in range(4):
            assert controller._background_slots.acquire(blocking=False)
        assert not controller._background_slots.acquire(blocking=False)


def test_shutdown_waits_for_owner_cleanup_and_ignores_stale_request(tmp_path):
    owner, caller = InstanceLock("qa", tmp_path), InstanceLock("qa", tmp_path)
    assert owner.acquire()
    owner.stop_path.write_text("0" * 32)
    assert not owner.stop_requested()
    cleanup_finished = threading.Event()

    def serve():
        deadline = time.monotonic() + 3
        while not owner.stop_requested() and time.monotonic() < deadline:
            time.sleep(0.01)
        time.sleep(0.1)  # simulate draining an admitted write
        cleanup_finished.set()
        owner.release()

    thread = threading.Thread(target=serve)
    thread.start()
    try:
        assert caller.request_stop(timeout=3)
        assert cleanup_finished.is_set()
    finally:
        thread.join()
    assert not owner.state_path.exists()
    assert not owner.stop_path.exists()


def test_stop_timeout_never_terminates_the_owner(tmp_path):
    with InstanceLock("qa", tmp_path) as owner:
        assert not InstanceLock("qa", tmp_path).request_stop(timeout=0.01)
        assert owner.stop_requested()
        assert not InstanceLock("qa", tmp_path).acquire()


def test_instance_publication_does_not_require_fchmod(tmp_path, monkeypatch):
    monkeypatch.delattr(os, "fchmod", raising=False)
    with InstanceLock("qa", tmp_path) as owner:
        owner.publish_url("http://127.0.0.1:38124/?token=test")
        assert owner.existing_url()
        owner.state_path.write_text('{"url":"http://127.0.0.1:invalid/?token=x"}')
        assert owner.existing_url() == ""


def test_log_rotates_during_one_process_lifetime(tmp_path):
    path = tmp_path / "agent.log"
    with patch("deck3ds.desktop.logging.MAX_LOG_SIZE", 512):
        stream = RotatingLog(path)
        try:
            for _ in range(40):
                stream.write("é" * 100)
            stream.flush()
            assert path.stat().st_size <= 512
            assert path.with_suffix(".log.1").stat().st_size <= 512
        finally:
            stream.close()

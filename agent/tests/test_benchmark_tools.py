"""Benchmark CLI output is usable and its resources are closed."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

AGENT = Path(__file__).resolve().parents[1]


def test_runtime_benchmark_outputs_json_and_closes_resources():
    result = subprocess.run(
        [
            sys.executable,
            "tools/benchmark_runtime.py",
            "--cycles",
            "1",
            "--requests",
            "4",
            "--keep-alive",
        ],
        cwd=AGENT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["scenario"] == "current-agent-http-tcp"
    assert len(report["cycles"]) == 1
    assert report["cycles"][0]["tasks_after_close"] == 0
    assert report["cycles"][0]["http_connections"] == 4


@pytest.mark.parametrize("arguments", [["--requests", "3"], ["--cycles", "0"]])
def test_runtime_benchmark_rejects_invalid_workload(arguments):
    result = subprocess.run(
        [sys.executable, "tools/benchmark_runtime.py", *arguments],
        cwd=AGENT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert not result.stdout

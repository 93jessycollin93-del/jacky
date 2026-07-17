#!/usr/bin/env python3
"""
tests/agent_tests/test_route_a_task.py — Unit tests for examples/route_a_task.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from examples import route_a_task


class _FakeAssessor:
    def __init__(self, status=None, raise_exc=None):
        self._status = status or {}
        self._raise_exc = raise_exc

    def assess(self):
        if self._raise_exc:
            raise self._raise_exc
        return self._status


class _FakeRouter:
    def __init__(self, response=None, raise_exc=None):
        self._response = response
        self._raise_exc = raise_exc

    def route(self, task):
        if self._raise_exc:
            raise self._raise_exc
        return self._response


def test_main_happy_path(monkeypatch, capsys):
    status = {
        "gpu_temp_c": 55,
        "cpu_percent": 12,
        "ram_percent": 40,
        "recommended_tier": "local",
    }
    monkeypatch.setattr(route_a_task, "SituationAssessor",
                         lambda: _FakeAssessor(status=status))
    monkeypatch.setattr(route_a_task, "CloudRouter",
                         lambda: _FakeRouter(response="42"))

    route_a_task.main()

    out = capsys.readouterr().out
    assert "GPU=55" in out
    assert "CPU=12" in out
    assert "RAM=40" in out
    assert "Recommended tier: local" in out
    assert "Response:\n42" in out


def test_main_handles_status_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        route_a_task, "SituationAssessor",
        lambda: _FakeAssessor(raise_exc=RuntimeError("no telemetry")),
    )
    monkeypatch.setattr(route_a_task, "CloudRouter",
                         lambda: _FakeRouter(response="ok"))

    route_a_task.main()

    out = capsys.readouterr().out
    assert "[WARN] Could not read system status: no telemetry" in out
    assert "Response:\nok" in out


def test_main_handles_routing_failure(monkeypatch, capsys):
    status = {"gpu_temp_c": 60, "cpu_percent": 20, "ram_percent": 50}
    monkeypatch.setattr(route_a_task, "SituationAssessor",
                         lambda: _FakeAssessor(status=status))
    monkeypatch.setattr(
        route_a_task, "CloudRouter",
        lambda: _FakeRouter(raise_exc=RuntimeError("all providers failed")),
    )

    route_a_task.main()

    out = capsys.readouterr().out
    assert "[ERROR] Routing failed: all providers failed" in out
    assert "Make sure at least one API key" in out


def test_main_uses_defaults_when_status_missing_keys(monkeypatch, capsys):
    monkeypatch.setattr(route_a_task, "SituationAssessor",
                         lambda: _FakeAssessor(status={}))
    monkeypatch.setattr(route_a_task, "CloudRouter",
                         lambda: _FakeRouter(response="ok"))

    route_a_task.main()

    out = capsys.readouterr().out
    assert "GPU=N/A" in out
    assert "CPU=?" in out
    assert "RAM=?" in out
    assert "Recommended tier: unknown" in out


def test_main_prints_the_expected_task_prompt(monkeypatch, capsys):
    monkeypatch.setattr(route_a_task, "SituationAssessor",
                         lambda: _FakeAssessor(status={}))
    monkeypatch.setattr(route_a_task, "CloudRouter",
                         lambda: _FakeRouter(response="ok"))

    route_a_task.main()

    out = capsys.readouterr().out
    assert "Summarise the purpose of jacky_core.py in one sentence." in out


def test_main_handles_router_missing_route_method(monkeypatch, capsys):
    """Regression: CloudRouter currently only exposes `.ask()`, not `.route()`.
    If main() is ever run against a router object without `.route()`, the
    resulting AttributeError must be caught, not propagated."""

    class _RouterWithoutRoute:
        pass

    monkeypatch.setattr(route_a_task, "SituationAssessor",
                         lambda: _FakeAssessor(status={}))
    monkeypatch.setattr(route_a_task, "CloudRouter",
                         lambda: _RouterWithoutRoute())

    route_a_task.main()  # must not raise

    out = capsys.readouterr().out
    assert "[ERROR] Routing failed:" in out
    assert "route" in out.lower()
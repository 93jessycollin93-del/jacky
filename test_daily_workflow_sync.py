#!/usr/bin/env python3
"""
Unit tests for the repo-mirror sync integration added to daily_workflow.py:
DailyWorkflow.sync_repos() and the new --sync-repos CLI flag in main().
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import daily_workflow
import sync_repos
import repo_mirror


@pytest.fixture
def workflow():
    return daily_workflow.DailyWorkflow(verbose=False)


class TestSyncRepos:
    def test_returns_zero_exit_code_from_sync_repos_main(self, workflow, monkeypatch):
        monkeypatch.setattr(sync_repos, "main", lambda argv: 0)
        monkeypatch.setattr(repo_mirror, "load_status", lambda: {"ok": 5, "errors": 0, "total": 5})

        result = workflow.sync_repos()
        assert result == 0

    def test_propagates_nonzero_exit_code_from_sync_repos_main(self, workflow, monkeypatch):
        monkeypatch.setattr(sync_repos, "main", lambda argv: 1)
        monkeypatch.setattr(repo_mirror, "load_status", lambda: {"ok": 3, "errors": 2, "total": 5})

        result = workflow.sync_repos()
        assert result == 1

    def test_calls_sync_repos_main_with_empty_argv(self, workflow, monkeypatch):
        captured = {}

        def fake_main(argv):
            captured["argv"] = argv
            return 0

        monkeypatch.setattr(sync_repos, "main", fake_main)
        monkeypatch.setattr(repo_mirror, "load_status", lambda: {})

        workflow.sync_repos()
        assert captured["argv"] == []

    def test_exception_from_sync_repos_is_caught_and_reports_failure(self, workflow, monkeypatch):
        def boom(argv):
            raise RuntimeError("git not installed")

        monkeypatch.setattr(sync_repos, "main", boom)

        result = workflow.sync_repos()
        assert result == 1

    def test_prints_ok_error_total_summary_line(self, workflow, monkeypatch, capsys):
        monkeypatch.setattr(sync_repos, "main", lambda argv: 0)
        monkeypatch.setattr(repo_mirror, "load_status", lambda: {"ok": 7, "errors": 1, "total": 8})

        workflow.sync_repos()
        out = capsys.readouterr().out
        assert "7 ok" in out
        assert "1 errors" in out
        assert "8 total repos" in out

    def test_missing_status_fields_default_to_zero_in_output(self, workflow, monkeypatch, capsys):
        monkeypatch.setattr(sync_repos, "main", lambda argv: 0)
        monkeypatch.setattr(repo_mirror, "load_status", lambda: {})

        workflow.sync_repos()
        out = capsys.readouterr().out
        assert "0 ok" in out
        assert "0 errors" in out
        assert "0 total repos" in out


class TestMainSyncFlagWiring:
    def test_sync_repos_invoked_when_flag_present(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["daily_workflow.py", "--sync-repos"])

        calls = []
        monkeypatch.setattr(
            daily_workflow.DailyWorkflow, "sync_repos",
            lambda self: calls.append("sync") or 0,
        )
        # Short-circuit before the network-dependent pulse run.
        monkeypatch.setattr(
            daily_workflow.DailyWorkflow, "check_system",
            lambda self: (False, {}),
        )

        exit_code = daily_workflow.main()
        assert calls == ["sync"]
        assert exit_code == 1  # system not ready, per stubbed check_system

    def test_sync_repos_not_invoked_without_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["daily_workflow.py"])

        calls = []
        monkeypatch.setattr(
            daily_workflow.DailyWorkflow, "sync_repos",
            lambda self: calls.append("sync") or 0,
        )
        monkeypatch.setattr(
            daily_workflow.DailyWorkflow, "check_system",
            lambda self: (False, {}),
        )

        daily_workflow.main()
        assert calls == []

    def test_sync_runs_before_system_check(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["daily_workflow.py", "--sync-repos"])

        order = []
        monkeypatch.setattr(
            daily_workflow.DailyWorkflow, "sync_repos",
            lambda self: order.append("sync") or 0,
        )
        monkeypatch.setattr(
            daily_workflow.DailyWorkflow, "check_system",
            lambda self: order.append("check_system") or (False, {}),
        )

        daily_workflow.main()
        assert order == ["sync", "check_system"]
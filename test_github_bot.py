#!/usr/bin/env python3
"""
Unit tests for bots/github_bot.py — specifically the local-mirror integration
added in this PR (_repo_source / _get_repos_status now prefer
scripts/sync_repos.py's local mirror over a live GitHub API call).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bots"))

import github_bot


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    monkeypatch.delenv("JACKY_REPOS_DIR", raising=False)


@pytest.fixture
def bot():
    return github_bot.GitHubBot()


class TestRepoSource:
    def test_returns_remote_when_no_local_mirror_found(self, bot, monkeypatch):
        monkeypatch.setattr(github_bot, "get_local_repo_path", lambda name: None)
        result = bot._repo_source("eru")
        assert result == {"source": "remote"}

    def test_returns_local_mirror_with_path_and_status_when_found(self, bot, monkeypatch, tmp_path):
        mirror_path = tmp_path / "eru"
        monkeypatch.setattr(github_bot, "get_local_repo_path", lambda name: mirror_path)
        monkeypatch.setattr(github_bot, "repo_status", lambda name: {"name": name, "status": "ok"})

        result = bot._repo_source("eru")

        assert result["source"] == "local_mirror"
        assert result["path"] == str(mirror_path)
        assert result["sync_status"] == {"name": "eru", "status": "ok"}

    def test_local_mirror_with_no_sync_status_yet_is_none(self, bot, monkeypatch, tmp_path):
        mirror_path = tmp_path / "neweru"
        monkeypatch.setattr(github_bot, "get_local_repo_path", lambda name: mirror_path)
        monkeypatch.setattr(github_bot, "repo_status", lambda name: None)

        result = bot._repo_source("neweru")

        assert result["source"] == "local_mirror"
        assert result["sync_status"] is None

    def test_passes_repo_name_through_to_lookup_helpers(self, bot, monkeypatch):
        seen = {}

        def fake_get_local_repo_path(name):
            seen["lookup_name"] = name
            return None

        monkeypatch.setattr(github_bot, "get_local_repo_path", fake_get_local_repo_path)
        bot._repo_source("cyber-store")
        assert seen["lookup_name"] == "cyber-store"


class TestGetReposStatus:
    def test_enriches_every_repo_with_source_info(self, bot, monkeypatch):
        monkeypatch.setattr(bot, "_repo_source", lambda name: {"source": "remote"})
        repos = bot._get_repos_status()
        assert len(repos) == 2
        assert all(r["source"] == "remote" for r in repos)

    def test_known_repo_names_are_present(self, bot, monkeypatch):
        monkeypatch.setattr(bot, "_repo_source", lambda name: {"source": "remote"})
        repos = bot._get_repos_status()
        names = {r["name"] for r in repos}
        assert names == {"cyber-store", "eru"}

    def test_preserves_original_status_fields(self, bot, monkeypatch):
        monkeypatch.setattr(bot, "_repo_source", lambda name: {"source": "remote"})
        repos = bot._get_repos_status()
        cyber_store = next(r for r in repos if r["name"] == "cyber-store")
        assert cyber_store["branch"] == "main"
        assert cyber_store["status"] == "\u2705 healthy"

    def test_each_repo_gets_its_own_source_lookup(self, bot, monkeypatch):
        calls = []

        def fake_repo_source(name):
            calls.append(name)
            return {"source": "remote"}

        monkeypatch.setattr(bot, "_repo_source", fake_repo_source)
        bot._get_repos_status()
        assert calls == ["cyber-store", "eru"]

    def test_end_to_end_local_mirror_detection(self, bot, monkeypatch, tmp_path):
        """Integration check: a real mirror directory for 'eru' should be
        picked up via the actual repo_mirror helpers (not mocked), while
        'cyber-store' (no mirror) should fall back to remote."""
        mirror_root = tmp_path / "mirror"
        eru_dir = mirror_root / "eru"
        (eru_dir / ".git").mkdir(parents=True)
        monkeypatch.setenv("JACKY_REPOS_DIR", str(mirror_root))

        repos = bot._get_repos_status()

        eru = next(r for r in repos if r["name"] == "eru")
        assert eru["source"] == "local_mirror"
        assert eru["path"] == str(eru_dir)

        cyber_store = next(r for r in repos if r["name"] == "cyber-store")
        assert cyber_store["source"] == "remote"


class TestHandleTaskStatusIntegration:
    def test_status_task_includes_enriched_repositories(self, bot, monkeypatch):
        monkeypatch.setattr(bot, "_repo_source", lambda name: {"source": "remote"})
        result = bot.handle_task({"type": "status"})
        assert result["status"] == "ok"
        assert "repositories" in result
        assert all(r["source"] == "remote" for r in result["repositories"])

    def test_unknown_task_type_still_returns_error(self, bot):
        result = bot.handle_task({"type": "bogus"})
        assert "error" in result
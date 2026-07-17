#!/usr/bin/env python3
"""
Unit tests for repo_mirror.py — the shared helper bots/agents use to find a
repo's local mirror (created by scripts/sync_repos.py) before falling back
to the GitHub API.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import repo_mirror


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """Never let a real JACKY_REPOS_DIR leak in from the host environment."""
    monkeypatch.delenv("JACKY_REPOS_DIR", raising=False)


@pytest.fixture
def repos_file(tmp_path, monkeypatch):
    """Point repo_mirror.REPOS_FILE at an isolated, per-test location."""
    path = tmp_path / "repos.json"
    monkeypatch.setattr(repo_mirror, "REPOS_FILE", path)
    return path


@pytest.fixture
def status_file(tmp_path, monkeypatch):
    """Point repo_mirror.STATUS_FILE at an isolated, per-test location."""
    path = tmp_path / "data" / "repo_mirror_status.json"
    monkeypatch.setattr(repo_mirror, "STATUS_FILE", path)
    return path


class TestLoadRepoConfig:
    def test_missing_file_returns_empty_dict(self, repos_file):
        assert repo_mirror._load_repo_config() == {}

    def test_valid_json_returns_parsed_dict(self, repos_file):
        repos_file.write_text(json.dumps({"default_owner": "acme", "repos": []}))
        cfg = repo_mirror._load_repo_config()
        assert cfg["default_owner"] == "acme"
        assert cfg["repos"] == []

    def test_invalid_json_returns_empty_dict(self, repos_file):
        repos_file.write_text("{not valid json")
        assert repo_mirror._load_repo_config() == {}


class TestGetReposDir:
    def test_env_var_takes_precedence_over_config(self, repos_file, monkeypatch, tmp_path):
        repos_file.write_text(json.dumps({"base_dir": str(tmp_path / "from_config")}))
        env_dir = tmp_path / "from_env"
        monkeypatch.setenv("JACKY_REPOS_DIR", str(env_dir))
        assert repo_mirror.get_repos_dir() == env_dir

    def test_config_base_dir_used_when_no_env(self, repos_file, tmp_path):
        cfg_dir = tmp_path / "from_config"
        repos_file.write_text(json.dumps({"base_dir": str(cfg_dir)}))
        assert repo_mirror.get_repos_dir() == cfg_dir

    def test_default_when_no_env_or_config(self, repos_file):
        repos_file.write_text(json.dumps({"repos": []}))
        assert repo_mirror.get_repos_dir() == repo_mirror.DEFAULT_BASE_DIR

    def test_default_when_repos_file_missing(self, repos_file):
        # repos_file fixture points REPOS_FILE somewhere that doesn't exist.
        assert repo_mirror.get_repos_dir() == repo_mirror.DEFAULT_BASE_DIR

    def test_env_var_path_is_expanded(self, repos_file, monkeypatch):
        monkeypatch.setenv("JACKY_REPOS_DIR", "~/mirrors")
        result = repo_mirror.get_repos_dir()
        assert "~" not in str(result)


class TestGetLocalRepoPath:
    def test_returns_path_when_git_dir_present(self, repos_file, tmp_path):
        repos_file.write_text(json.dumps({"base_dir": str(tmp_path)}))
        repo_dir = tmp_path / "myrepo"
        (repo_dir / ".git").mkdir(parents=True)
        result = repo_mirror.get_local_repo_path("myrepo")
        assert result == repo_dir

    def test_returns_none_when_repo_dir_missing(self, repos_file, tmp_path):
        repos_file.write_text(json.dumps({"base_dir": str(tmp_path)}))
        assert repo_mirror.get_local_repo_path("ghost-repo") is None

    def test_returns_none_when_dir_exists_but_not_a_git_repo(self, repos_file, tmp_path):
        repos_file.write_text(json.dumps({"base_dir": str(tmp_path)}))
        repo_dir = tmp_path / "myrepo"
        repo_dir.mkdir()
        assert repo_mirror.get_local_repo_path("myrepo") is None

    def test_treats_git_file_as_valid_repo_marker(self, repos_file, tmp_path):
        # Worktrees/submodules use a .git *file* rather than a directory;
        # get_local_repo_path only checks existence, so this should count.
        repos_file.write_text(json.dumps({"base_dir": str(tmp_path)}))
        repo_dir = tmp_path / "myrepo"
        repo_dir.mkdir()
        (repo_dir / ".git").write_text("gitdir: ../somewhere")
        assert repo_mirror.get_local_repo_path("myrepo") == repo_dir

    def test_returns_none_when_target_is_a_file_not_a_dir(self, repos_file, tmp_path):
        repos_file.write_text(json.dumps({"base_dir": str(tmp_path)}))
        (tmp_path / "myrepo").write_text("not a directory")
        assert repo_mirror.get_local_repo_path("myrepo") is None


class TestLoadStatus:
    def test_missing_file_returns_default_summary(self, status_file):
        result = repo_mirror.load_status()
        assert result == {"generated_at": None, "total": 0, "ok": 0, "errors": 0, "repos": []}

    def test_valid_file_returns_parsed_content(self, status_file):
        payload = {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "total": 2,
            "ok": 1,
            "errors": 1,
            "repos": [
                {"name": "eru", "status": "ok"},
                {"name": "neweru", "status": "error"},
            ],
        }
        status_file.parent.mkdir(parents=True)
        status_file.write_text(json.dumps(payload))
        assert repo_mirror.load_status() == payload

    def test_invalid_json_returns_default_summary(self, status_file):
        status_file.parent.mkdir(parents=True)
        status_file.write_text("not json{{{")
        result = repo_mirror.load_status()
        assert result["total"] == 0
        assert result["repos"] == []


class TestRepoStatus:
    def test_returns_entry_when_present(self, status_file):
        payload = {"repos": [{"name": "eru", "status": "ok"}, {"name": "neweru", "status": "error"}]}
        status_file.parent.mkdir(parents=True)
        status_file.write_text(json.dumps(payload))
        entry = repo_mirror.repo_status("neweru")
        assert entry == {"name": "neweru", "status": "error"}

    def test_returns_none_when_repo_unknown(self, status_file):
        payload = {"repos": [{"name": "eru", "status": "ok"}]}
        status_file.parent.mkdir(parents=True)
        status_file.write_text(json.dumps(payload))
        assert repo_mirror.repo_status("missing-repo") is None

    def test_returns_none_when_status_file_missing(self, status_file):
        assert repo_mirror.repo_status("anything") is None
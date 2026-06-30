#!/usr/bin/env python3
"""
Unit tests for scripts/sync_repos.py — cross-platform repo mirroring used to
populate the local mirror that repo_mirror.py / bots/github_bot.py read from.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import sync_repos


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    monkeypatch.delenv("JACKY_REPOS_DIR", raising=False)


@pytest.fixture
def repos_file(tmp_path, monkeypatch):
    path = tmp_path / "repos.json"
    monkeypatch.setattr(sync_repos, "REPOS_FILE", path)
    return path


@pytest.fixture
def status_file(tmp_path, monkeypatch):
    path = tmp_path / "data" / "repo_mirror_status.json"
    monkeypatch.setattr(sync_repos, "STATUS_FILE", path)
    return path


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestLoadRepoConfig:
    def test_missing_file_returns_empty_defaults(self, repos_file):
        cfg = sync_repos.load_repo_config()
        assert cfg == {"default_owner": "", "repos": []}

    def test_valid_file_is_parsed(self, repos_file):
        repos_file.write_text(json.dumps({"default_owner": "acme", "repos": [{"name": "a"}]}))
        cfg = sync_repos.load_repo_config()
        assert cfg["default_owner"] == "acme"
        assert cfg["repos"] == [{"name": "a"}]


class TestResolveBaseDir:
    def test_cli_flag_wins_over_env_and_config(self, monkeypatch, tmp_path):
        monkeypatch.setenv("JACKY_REPOS_DIR", str(tmp_path / "env"))
        config = {"base_dir": str(tmp_path / "config")}
        result = sync_repos.resolve_base_dir(str(tmp_path / "cli"), config)
        assert result == tmp_path / "cli"

    def test_env_var_wins_when_no_cli_flag(self, monkeypatch, tmp_path):
        monkeypatch.setenv("JACKY_REPOS_DIR", str(tmp_path / "env"))
        config = {"base_dir": str(tmp_path / "config")}
        result = sync_repos.resolve_base_dir(None, config)
        assert result == tmp_path / "env"

    def test_config_base_dir_used_when_no_cli_or_env(self, tmp_path):
        config = {"base_dir": str(tmp_path / "config")}
        result = sync_repos.resolve_base_dir(None, config)
        assert result == tmp_path / "config"

    def test_default_used_when_nothing_is_set(self):
        result = sync_repos.resolve_base_dir(None, {})
        assert result == sync_repos.DEFAULT_BASE_DIR


class TestBuildCloneUrl:
    def test_without_token_uses_plain_https(self):
        url = sync_repos.build_clone_url("acme", "widgets", None)
        assert url == "https://github.com/acme/widgets.git"

    def test_with_token_embeds_credential(self):
        url = sync_repos.build_clone_url("acme", "widgets", "TOKEN123")
        assert url == "https://TOKEN123@github.com/acme/widgets.git"

    def test_with_empty_string_token_behaves_like_no_token(self):
        url = sync_repos.build_clone_url("acme", "widgets", "")
        assert url == "https://github.com/acme/widgets.git"


class TestSyncOneDryRun:
    def test_dry_run_reports_clone_when_target_missing(self, tmp_path):
        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=True)
        assert entry["action"] == "clone"
        assert entry["status"] == "skipped"
        assert entry["last_synced"] is None
        assert entry["error"] is None

    def test_dry_run_reports_pull_when_target_present(self, tmp_path):
        (tmp_path / "widgets").mkdir()
        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=True)
        assert entry["action"] == "pull"
        assert entry["status"] == "skipped"

    def test_dry_run_never_touches_disk(self, tmp_path):
        repo = {"name": "widgets"}
        sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=True)
        assert not (tmp_path / "widgets").exists()


class TestSyncOneRealRun:
    def test_clone_success_invokes_git_clone(self, monkeypatch, tmp_path):
        captured = {}

        def fake_run_git(args, cwd=None):
            captured["args"] = args
            captured["cwd"] = cwd
            return FakeCompletedProcess(returncode=0)

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)

        assert entry["action"] == "clone"
        assert entry["status"] == "ok"
        assert entry["error"] is None
        assert entry["last_synced"] is not None
        assert captured["args"][0] == "clone"
        assert "acme/widgets.git" in captured["args"][1]
        assert captured["args"][2] == str(tmp_path / "widgets")

    def test_pull_success_invokes_git_pull_in_target_dir(self, monkeypatch, tmp_path):
        target = tmp_path / "widgets"
        target.mkdir()
        captured = {}

        def fake_run_git(args, cwd=None):
            captured["args"] = args
            captured["cwd"] = cwd
            return FakeCompletedProcess(returncode=0)

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)

        assert entry["action"] == "pull"
        assert entry["status"] == "ok"
        assert captured["args"] == ["pull", "--ff-only"]
        assert captured["cwd"] == target

    def test_clone_failure_records_stderr_as_error(self, monkeypatch, tmp_path):
        def fake_run_git(args, cwd=None):
            return FakeCompletedProcess(returncode=128, stderr="fatal: repository not found")

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)

        assert entry["status"] == "error"
        assert "repository not found" in entry["error"]

    def test_failure_falls_back_to_stdout_when_no_stderr(self, monkeypatch, tmp_path):
        def fake_run_git(args, cwd=None):
            return FakeCompletedProcess(returncode=1, stdout="something went wrong", stderr="")

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)

        assert entry["status"] == "error"
        assert "something went wrong" in entry["error"]

    def test_timeout_is_caught_and_reported(self, monkeypatch, tmp_path):
        def fake_run_git(args, cwd=None):
            raise subprocess.TimeoutExpired(cmd="git", timeout=300)

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)

        assert entry["status"] == "error"
        assert entry["error"] == "git operation timed out"

    def test_generic_exception_is_caught_and_reported(self, monkeypatch, tmp_path):
        def fake_run_git(args, cwd=None):
            raise OSError("disk full")

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)

        assert entry["status"] == "error"
        assert "disk full" in entry["error"]

    def test_per_repo_owner_override_is_used_in_clone_url(self, monkeypatch, tmp_path):
        captured = {}

        def fake_run_git(args, cwd=None):
            captured["args"] = args
            return FakeCompletedProcess(returncode=0)

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets", "owner": "other-owner"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)

        assert entry["owner"] == "other-owner"
        assert "other-owner/widgets.git" in captured["args"][1]

    def test_per_repo_path_override_changes_target_directory(self, monkeypatch, tmp_path):
        def fake_run_git(args, cwd=None):
            return FakeCompletedProcess(returncode=0)

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets", "path": "custom-folder"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)

        assert entry["path"] == str(tmp_path / "custom-folder")

    def test_missing_tag_defaults_to_unspecified(self, monkeypatch, tmp_path):
        def fake_run_git(args, cwd=None):
            return FakeCompletedProcess(returncode=0)

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)
        assert entry["tag"] == "unspecified"

    def test_error_message_is_truncated_to_500_chars(self, monkeypatch, tmp_path):
        def fake_run_git(args, cwd=None):
            return FakeCompletedProcess(returncode=1, stderr="x" * 1000)

        monkeypatch.setattr(sync_repos, "run_git", fake_run_git)

        repo = {"name": "widgets"}
        entry = sync_repos.sync_one(repo, "acme", tmp_path, None, dry_run=False)
        assert len(entry["error"]) == 500


class TestFilterRepos:
    REPOS = [
        {"name": "a", "tag": "condenser"},
        {"name": "b", "tag": "bot"},
        {"name": "c", "tag": "condenser"},
    ]

    def test_no_filter_returns_all_repos_unchanged(self):
        assert sync_repos.filter_repos(self.REPOS, None) == self.REPOS

    def test_filters_by_single_tag(self):
        result = sync_repos.filter_repos(self.REPOS, ["bot"])
        assert result == [{"name": "b", "tag": "bot"}]

    def test_filters_by_multiple_tags(self):
        result = sync_repos.filter_repos(self.REPOS, ["bot", "condenser"])
        assert result == self.REPOS

    def test_strips_whitespace_around_tags(self):
        result = sync_repos.filter_repos(self.REPOS, [" bot ", " condenser "])
        assert len(result) == 3

    def test_unknown_tag_returns_empty_list(self):
        assert sync_repos.filter_repos(self.REPOS, ["nonexistent"]) == []


class TestWriteStatus:
    def test_writes_summary_with_correct_counts(self, status_file):
        results = [
            {"name": "a", "status": "ok"},
            {"name": "b", "status": "error"},
            {"name": "c", "status": "ok"},
        ]
        sync_repos.write_status(results)

        assert status_file.exists()
        saved = json.loads(status_file.read_text())
        assert saved["total"] == 3
        assert saved["ok"] == 2
        assert saved["errors"] == 1
        assert saved["repos"] == results
        assert saved["generated_at"] is not None

    def test_creates_parent_directory_if_missing(self, status_file):
        assert not status_file.parent.exists()
        sync_repos.write_status([])
        assert status_file.parent.exists()

    def test_handles_empty_results_list(self, status_file):
        sync_repos.write_status([])
        saved = json.loads(status_file.read_text())
        assert saved["total"] == 0
        assert saved["ok"] == 0
        assert saved["errors"] == 0


class TestMain:
    def test_dry_run_exits_zero_and_skips_status_write(self, repos_file, status_file, tmp_path):
        repos_file.write_text(json.dumps({
            "default_owner": "acme",
            "repos": [{"name": "widgets"}],
        }))
        exit_code = sync_repos.main(["--base-dir", str(tmp_path / "mirror"), "--dry-run"])
        assert exit_code == 0
        assert not status_file.exists()

    def test_no_repos_in_config_returns_nonzero(self, repos_file):
        repos_file.write_text(json.dumps({"default_owner": "acme", "repos": []}))
        exit_code = sync_repos.main([])
        assert exit_code == 1

    def test_only_filter_narrows_which_repos_are_synced(self, monkeypatch, repos_file, status_file, tmp_path):
        repos_file.write_text(json.dumps({
            "default_owner": "acme",
            "repos": [
                {"name": "a", "tag": "condenser"},
                {"name": "b", "tag": "bot"},
            ],
        }))
        seen = []

        def fake_sync_one(repo, owner, base_dir, token, dry_run):
            seen.append(repo["name"])
            return {"name": repo["name"], "status": "ok"}

        monkeypatch.setattr(sync_repos, "sync_one", fake_sync_one)

        exit_code = sync_repos.main(["--base-dir", str(tmp_path), "--only", "bot"])
        assert exit_code == 0
        assert seen == ["b"]

    def test_errors_in_results_yield_nonzero_exit_and_writes_status(self, monkeypatch, repos_file, status_file, tmp_path):
        repos_file.write_text(json.dumps({
            "default_owner": "acme",
            "repos": [{"name": "widgets"}],
        }))
        monkeypatch.setattr(
            sync_repos, "sync_one",
            lambda repo, owner, base_dir, token, dry_run: {"name": "widgets", "status": "error"},
        )

        exit_code = sync_repos.main(["--base-dir", str(tmp_path)])
        assert exit_code == 1
        assert status_file.exists()

    def test_all_ok_results_yield_zero_exit(self, monkeypatch, repos_file, status_file, tmp_path):
        repos_file.write_text(json.dumps({
            "default_owner": "acme",
            "repos": [{"name": "widgets"}, {"name": "gadgets"}],
        }))
        monkeypatch.setattr(
            sync_repos, "sync_one",
            lambda repo, owner, base_dir, token, dry_run: {"name": repo["name"], "status": "ok"},
        )

        exit_code = sync_repos.main(["--base-dir", str(tmp_path)])
        assert exit_code == 0
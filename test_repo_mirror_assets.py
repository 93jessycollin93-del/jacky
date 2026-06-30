#!/usr/bin/env python3
"""
Tests for the supporting assets of the repo-mirror feature introduced in this
PR: .gitignore entries, the slimmed-down Windows wrapper script, and basic
consistency checks between the new documentation and the actual
implementation (so docs/code can't silently drift apart).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


class TestGitignore:
    @staticmethod
    def _content():
        return (ROOT / ".gitignore").read_text()

    def test_excludes_mirrored_repos_directory(self):
        assert "repo_mirror/" in self._content()

    def test_excludes_status_file(self):
        assert "repo_mirror_status.json" in self._content()

    def test_mirror_entries_have_explanatory_comment(self):
        lines = self._content().splitlines()
        idx = lines.index("repo_mirror/")
        assert lines[idx - 1].lstrip().startswith("#")


class TestCloneAllReposBat:
    @staticmethod
    def _content():
        return (ROOT / "scripts" / "clone_all_repos.bat").read_text()

    def test_delegates_to_sync_repos_script(self):
        assert "sync_repos.py" in self._content()

    def test_sets_default_jacky_repos_dir_when_unset(self):
        content = self._content()
        assert 'IF "%JACKY_REPOS_DIR%"==""' in content
        assert "SET JACKY_REPOS_DIR=" in content

    def test_no_longer_hardcodes_the_repo_list(self):
        # The old .bat enumerated every repo name inline; repos.json is now
        # the single source of truth, so the wrapper shouldn't duplicate it.
        content = self._content()
        assert "neutronknowledge" not in content
        assert "FOR %%R IN" not in content

    def test_passes_base_dir_flag_through_to_sync_repos(self):
        assert "--base-dir" in self._content()


class TestDocConsistency:
    """Sanity-check that the new docs reference things that actually exist
    in the implementation."""

    def test_architecture_md_describes_repo_mirror_system(self):
        content = (ROOT / "ARCHITECTURE.md").read_text()
        assert "Repo Mirror System" in content
        assert "repos.json" in content
        assert "scripts/sync_repos.py" in content
        assert "repo_mirror.py" in content

    def test_operational_guide_documents_sync_repos_flag(self):
        content = (ROOT / "OPERATIONAL_GUIDE.md").read_text()
        assert "--sync-repos" in content

    def test_repo_mirror_guide_exists(self):
        assert (ROOT / "REPO_MIRROR_GUIDE.md").exists()

    def test_repo_mirror_guide_documents_helper_functions(self):
        content = (ROOT / "REPO_MIRROR_GUIDE.md").read_text()
        assert "get_local_repo_path" in content
        assert "repo_status" in content
        assert "JACKY_REPOS_DIR" in content

    def test_documented_helper_functions_actually_exist_in_repo_mirror(self):
        import repo_mirror

        assert hasattr(repo_mirror, "get_local_repo_path")
        assert hasattr(repo_mirror, "repo_status")
        assert hasattr(repo_mirror, "load_status")
        assert hasattr(repo_mirror, "get_repos_dir")
        assert callable(repo_mirror.get_local_repo_path)

    def test_documented_cli_flags_actually_exist_in_sync_repos_script(self):
        content = (ROOT / "scripts" / "sync_repos.py").read_text()
        for flag in ("--base-dir", "--only", "--dry-run"):
            assert flag in content

    def test_documented_sync_repos_flag_actually_exists_in_daily_workflow(self):
        content = (ROOT / "daily_workflow.py").read_text()
        assert "--sync-repos" in content
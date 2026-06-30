#!/usr/bin/env python3
"""
Schema/sanity tests for repos.json — the single source of truth read by
scripts/sync_repos.py and repo_mirror.py.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPOS_JSON = ROOT / "repos.json"


def _load():
    return json.loads(REPOS_JSON.read_text())


class TestReposJsonStructure:
    def test_file_exists(self):
        assert REPOS_JSON.exists()

    def test_file_is_valid_json(self):
        _load()  # should not raise

    def test_has_default_owner_string(self):
        cfg = _load()
        assert isinstance(cfg.get("default_owner"), str)
        assert cfg["default_owner"]

    def test_has_nonempty_repos_list(self):
        cfg = _load()
        assert isinstance(cfg["repos"], list)
        assert len(cfg["repos"]) > 0

    def test_every_repo_has_name_and_tag(self):
        cfg = _load()
        for repo in cfg["repos"]:
            assert "name" in repo and repo["name"], repo
            assert "tag" in repo and repo["tag"], repo

    def test_repo_names_are_unique(self):
        cfg = _load()
        names = [r["name"] for r in cfg["repos"]]
        assert len(names) == len(set(names))

    def test_tags_are_known_categories(self):
        cfg = _load()
        known_tags = {"condenser", "bot", "knowledge-source", "core"}
        unknown = {r["tag"] for r in cfg["repos"]} - known_tags
        assert not unknown, f"unexpected tag(s): {unknown}"

    def test_jacky_repo_present_and_tagged_core(self):
        cfg = _load()
        jacky = next((r for r in cfg["repos"] if r["name"] == "jacky"), None)
        assert jacky is not None
        assert jacky["tag"] == "core"

    def test_no_base_dir_committed_by_default(self):
        # repos.json may optionally carry a "base_dir" override, but the
        # checked-in version should rely on the script defaults / env var
        # instead of hardcoding a machine-specific path.
        cfg = _load()
        assert "base_dir" not in cfg or not cfg["base_dir"]

    def test_optional_owner_and_path_overrides_are_strings_when_present(self):
        cfg = _load()
        for repo in cfg["repos"]:
            if "owner" in repo:
                assert isinstance(repo["owner"], str) and repo["owner"]
            if "path" in repo:
                assert isinstance(repo["path"], str) and repo["path"]
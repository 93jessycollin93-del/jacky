#!/usr/bin/env python3
"""
repo_mirror.py — Shared helper so any bot/agent can find a repo's local
mirror (created by scripts/sync_repos.py) before falling back to the
GitHub API.

Convention:
  - Mirrored repos live under JACKY_REPOS_DIR (env var), or the "base_dir"
    field in repos.json, or the default data/repo_mirror/ folder.
  - scripts/sync_repos.py writes data/repo_mirror_status.json after each
    sync run with per-repo status + last_synced timestamps.

Usage:
    from repo_mirror import get_local_repo_path, repo_status

    path = get_local_repo_path("eru")
    if path:
        # read files straight from the local mirror
        ...
    else:
        # fall back to GitHub API
        ...
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("RepoMirror")

JACKY_HOME = Path(__file__).resolve().parent
REPOS_FILE = JACKY_HOME / "repos.json"
DEFAULT_BASE_DIR = JACKY_HOME / "data" / "repo_mirror"
STATUS_FILE = JACKY_HOME / "data" / "repo_mirror_status.json"


def _load_repo_config() -> Dict[str, Any]:
    if not REPOS_FILE.exists():
        return {}
    try:
        with open(REPOS_FILE) as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        log.warning(f"failed reading {REPOS_FILE.name}: {e}")
        return {}


def get_repos_dir() -> Path:
    """Resolve the base directory where mirrored repos live, honoring the
    same precedence as scripts/sync_repos.py."""
    env_value = os.getenv("JACKY_REPOS_DIR")
    if env_value:
        return Path(env_value).expanduser()
    config = _load_repo_config()
    if config.get("base_dir"):
        return Path(config["base_dir"]).expanduser()
    return DEFAULT_BASE_DIR


def get_local_repo_path(name: str) -> Optional[Path]:
    """Return the local mirror path for a repo if it exists on disk,
    otherwise None (caller should fall back to the GitHub API)."""
    candidate = get_repos_dir() / name
    if candidate.is_dir() and (candidate / ".git").exists():
        return candidate
    return None


def load_status() -> Dict[str, Any]:
    """Return the last sync_repos.py status report, or an empty summary if
    it has never been run."""
    if not STATUS_FILE.exists():
        return {"generated_at": None, "total": 0, "ok": 0, "errors": 0, "repos": []}
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        log.warning(f"failed reading {STATUS_FILE.name}: {e}")
        return {"generated_at": None, "total": 0, "ok": 0, "errors": 0, "repos": []}


def repo_status(name: str) -> Optional[Dict[str, Any]]:
    """Return the last sync status entry for a single repo, if known."""
    for entry in load_status().get("repos", []):
        if entry.get("name") == name:
            return entry
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    status = load_status()
    print(f"Repos dir: {get_repos_dir()}")
    print(f"Last sync: {status.get('generated_at')} "
          f"({status.get('ok', 0)} ok, {status.get('errors', 0)} errors, {status.get('total', 0)} total)")

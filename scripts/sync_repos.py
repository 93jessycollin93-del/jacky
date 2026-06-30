#!/usr/bin/env python3
"""
sync_repos.py — Cross-platform repo mirroring for the Jacky fleet.

Reads the repo list from repos.json (single source of truth) and, for each
entry, clones it if missing or pulls it if already present. Replaces the
Windows-only scripts/clone_all_repos.bat with logic that runs the same way
on Linux, macOS, and Windows.

Mirrored repos are written to a base directory so other bots/agents
(github_bot.py, squad_manager.py, etc.) can read local copies instead of
hitting the GitHub API every time. The base directory is configurable via:
  1. --base-dir CLI flag
  2. JACKY_REPOS_DIR environment variable
  3. repos.json "base_dir" field (if present)
  4. fallback default: <repo_root>/data/repo_mirror

After each run, a JSON status file is written (default:
data/repo_mirror_status.json) with per-repo success/failure and timestamps,
so other components can check sync health without re-running git.

Usage:
  python scripts/sync_repos.py
  python scripts/sync_repos.py --base-dir /mnt/superagent/condensers
  python scripts/sync_repos.py --only condenser,bot
  python scripts/sync_repos.py --dry-run
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("SyncRepos")

JACKY_HOME = Path(__file__).resolve().parent.parent
REPOS_FILE = JACKY_HOME / "repos.json"
DEFAULT_BASE_DIR = JACKY_HOME / "data" / "repo_mirror"
STATUS_FILE = JACKY_HOME / "data" / "repo_mirror_status.json"

# Reuse the project's own secret loading rules for private-repo auth.
sys.path.insert(0, str(JACKY_HOME))
try:
    from secrets_loader import get_secret
except ImportError:  # pragma: no cover - allows standalone use
    def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(name, default)


def load_repo_config() -> Dict[str, Any]:
    if not REPOS_FILE.exists():
        log.error(f"Repo list not found: {REPOS_FILE}")
        return {"default_owner": "", "repos": []}
    with open(REPOS_FILE) as f:
        return json.load(f)


def resolve_base_dir(cli_value: Optional[str], config: Dict[str, Any]) -> Path:
    if cli_value:
        return Path(cli_value).expanduser()
    env_value = os.getenv("JACKY_REPOS_DIR")
    if env_value:
        return Path(env_value).expanduser()
    if config.get("base_dir"):
        return Path(config["base_dir"]).expanduser()
    return DEFAULT_BASE_DIR


def build_clone_url(owner: str, name: str, token: Optional[str]) -> str:
    if token:
        return f"https://{token}@github.com/{owner}/{name}.git"
    return f"https://github.com/{owner}/{name}.git"


def run_git(args: List[str], cwd: Optional[Path] = None) -> "subprocess.CompletedProcess":
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=300,
    )


def sync_one(repo: Dict[str, Any], owner: str, base_dir: Path, token: Optional[str],
             dry_run: bool) -> Dict[str, Any]:
    name = repo["name"]
    repo_owner = repo.get("owner", owner)
    target_path = base_dir / repo.get("path", name)
    entry = {
        "name": name,
        "owner": repo_owner,
        "tag": repo.get("tag", "unspecified"),
        "path": str(target_path),
        "last_synced": None,
        "status": "skipped" if dry_run else "pending",
        "action": None,
        "error": None,
    }

    if dry_run:
        entry["action"] = "pull" if target_path.exists() else "clone"
        log.info(f"[dry-run] would {entry['action']} {repo_owner}/{name} -> {target_path}")
        return entry

    url = build_clone_url(repo_owner, name, token)

    try:
        if target_path.exists():
            entry["action"] = "pull"
            result = run_git(["pull", "--ff-only"], cwd=target_path)
        else:
            entry["action"] = "clone"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            result = run_git(["clone", url, str(target_path)])

        if result.returncode == 0:
            entry["status"] = "ok"
        else:
            entry["status"] = "error"
            entry["error"] = (result.stderr or result.stdout or "unknown git error").strip()[-500:]
    except subprocess.TimeoutExpired:
        entry["status"] = "error"
        entry["error"] = "git operation timed out"
    except Exception as e:  # noqa: BLE001 - we want to record any failure
        entry["status"] = "error"
        entry["error"] = str(e)

    entry["last_synced"] = datetime.now(timezone.utc).isoformat()
    log.info(f"  {entry['action']:5} {repo_owner}/{name}: {entry['status']}"
              + (f" ({entry['error']})" if entry["error"] else ""))
    return entry


def filter_repos(repos: List[Dict[str, Any]], only_tags: Optional[List[str]]) -> List[Dict[str, Any]]:
    if not only_tags:
        return repos
    only_tags = {t.strip() for t in only_tags}
    return [r for r in repos if r.get("tag") in only_tags]


def write_status(results: List[Dict[str, Any]]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "repos": results,
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    log.info(f"Status written to {STATUS_FILE}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Mirror Jacky fleet repos locally.")
    parser.add_argument("--base-dir", help="Directory to mirror repos into "
                                            "(overrides JACKY_REPOS_DIR env var).")
    parser.add_argument("--only", help="Comma-separated list of tags to sync "
                                        "(e.g. condenser,bot).")
    parser.add_argument("--dry-run", action="store_true",
                         help="Show what would happen without touching git or disk.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    config = load_repo_config()
    base_dir = resolve_base_dir(args.base_dir, config)
    owner = config.get("default_owner", "")
    repos = filter_repos(config.get("repos", []), args.only.split(",") if args.only else None)

    if not repos:
        log.warning("No repos to sync (check repos.json / --only filter).")
        return 1

    token = get_secret("GITHUB_TOKEN")

    log.info(f"Syncing {len(repos)} repo(s) into {base_dir}"
              + (" [dry-run]" if args.dry_run else ""))

    results = [sync_one(r, owner, base_dir, token, args.dry_run) for r in repos]

    if not args.dry_run:
        write_status(results)

    ok = sum(1 for r in results if r["status"] == "ok")
    errors = sum(1 for r in results if r["status"] == "error")
    log.info(f"\nDone: {ok} ok, {errors} errors, {len(results)} total.")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

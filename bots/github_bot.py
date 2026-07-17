#!/usr/bin/env python3
"""
GitHub Bot - Manages repos, PRs, branches, deployments
Uses GitHub API via requests library.
Reports back to Jacky.
"""

import logging
<<<<<<< HEAD
import os
=======
import sys
from pathlib import Path
>>>>>>> origin/main
from typing import Dict, Any, List
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from repo_mirror import get_local_repo_path, repo_status  # noqa: E402

log = logging.getLogger("GitHubBot")

class GitHubBot:
    """Jacky's GitHub manager — queries real GitHub API."""

    def __init__(self, token: str = None):
        self.name = "github_bot"
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.base_url = "https://api.github.com"
        self.username = "93jessycollin93-del"
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        log.info(f"GitHub Bot ready (user: {self.username})")

    def _repo_source(self, name: str) -> Dict[str, Any]:
        """Prefer a local mirror (scripts/sync_repos.py) over a live GitHub
        API call for read-only/status lookups. Falls back to "remote" when
        no fresh local mirror is available."""
        local_path = get_local_repo_path(name)
        if local_path:
            return {"source": "local_mirror", "path": str(local_path),
                     "sync_status": repo_status(name)}
        return {"source": "remote"}

    def handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a GitHub-related task."""
        task_type = task.get("type", "status")

        try:
            if task_type == "status":
                result = {
                    "status": "ok",
                    "repositories": self._get_repos_status(),
                    "prs": self._get_pending_prs(),
                    "branches": self._get_stale_branches(),
                    "timestamp": datetime.now().isoformat()
                }

            elif task_type == "merge_pr":
                pr_id = task.get("pr_id")
                repo = task.get("repo")
                result = self._merge_pr(repo, pr_id)

            elif task_type == "run_workflow":
                repo = task.get("repo")
                workflow = task.get("workflow")
                result = self._trigger_workflow(repo, workflow)

            else:
                result = {"error": f"Unknown task type: {task_type}"}

        except Exception as e:
            log.error(f"GitHub task {task_type} failed: {e}")
            result = {"error": str(e), "task_type": task_type}

        log.info(f"GitHub task {task_type} complete")
        return result

    def _get_repos_status(self) -> List[Dict[str, Any]]:
<<<<<<< HEAD
        """Status of your repos (via API)."""
        import requests
        try:
            resp = requests.get(
                f"{self.base_url}/user/repos",
                headers=self.headers,
                params={"sort": "updated", "per_page": 10},
                timeout=10
            )
            if resp.status_code != 200:
                log.warning(f"GitHub API returned {resp.status_code}")
                return []

            repos = []
            for r in resp.json():
                repos.append({
                    "name": r["name"],
                    "url": r["html_url"],
                    "branch": r.get("default_branch", "main"),
                    "last_commit": r.get("pushed_at", "unknown"),
                    "status": "✅ healthy",
                    "stars": r["stargazers_count"]
                })
            return repos
        except Exception as e:
            log.error(f"Failed to fetch repos: {e}")
            return []
=======
        """Status of all your repos.

        Checks the local mirror (scripts/sync_repos.py) first; falls back
        to the GitHub API (not yet implemented) when no mirror is present.
        """
        # Would call GitHub API
        repos = [
            {
                "name": "cyber-store",
                "branch": "main",
                "last_commit": "2 hours ago",
                "status": "✅ healthy"
            },
            {
                "name": "eru",
                "branch": "feature/jackie-animation-customization",
                "last_commit": "10 min ago",
                "status": "✅ healthy"
            }
        ]
        for r in repos:
            r.update(self._repo_source(r["name"]))
        return repos
>>>>>>> origin/main

    def _get_pending_prs(self) -> List[Dict[str, Any]]:
        """PRs awaiting review or action."""
        import requests
        try:
            resp = requests.get(
                f"{self.base_url}/search/issues",
                headers=self.headers,
                params={"q": f"user:{self.username} is:pr is:open", "per_page": 10},
                timeout=10
            )
            if resp.status_code != 200:
                log.warning(f"GitHub API returned {resp.status_code}")
                return []

            prs = []
            for item in resp.json().get("items", []):
                age_hours = (datetime.now(item["created_at"].tzinfo) - item["created_at"]).total_seconds() / 3600
                prs.append({
                    "repo": item["repository_url"].split("/")[-1],
                    "number": item["number"],
                    "title": item["title"],
                    "url": item["html_url"],
                    "status": "open",
                    "age_hours": int(age_hours)
                })
            return prs
        except Exception as e:
            log.error(f"Failed to fetch PRs: {e}")
            return []

    def _get_stale_branches(self) -> List[Dict[str, Any]]:
        """Branches that haven't been touched in a while."""
        import requests
        try:
            resp = requests.get(
                f"{self.base_url}/user/repos",
                headers=self.headers,
                params={"per_page": 20},
                timeout=10
            )
            if resp.status_code != 200:
                return []

            stale = []
            cutoff = datetime.now() - timedelta(days=7)
            for repo in resp.json():
                if repo["pushed_at"]:
                    last_push = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
                    if last_push < cutoff:
                        stale.append({
                            "repo": repo["name"],
                            "branch": repo.get("default_branch", "main"),
                            "days_since_update": (datetime.now(last_push.tzinfo) - last_push).days
                        })
            return stale
        except Exception as e:
            log.error(f"Failed to check stale branches: {e}")
            return []

    def _merge_pr(self, repo: str, pr_id: int) -> Dict[str, Any]:
        """Merge a PR (requires authentication and permission)."""
        import requests
        try:
            resp = requests.put(
                f"{self.base_url}/repos/{self.username}/{repo}/pulls/{pr_id}/merge",
                headers=self.headers,
                json={"commit_title": f"Auto-merge PR #{pr_id}", "merge_method": "squash"},
                timeout=10
            )
            if resp.status_code == 200:
                return {"status": "merged", "repo": repo, "pr": pr_id, "message": resp.json().get("message")}
            else:
                return {"status": "failed", "repo": repo, "pr": pr_id, "error": resp.text}
        except Exception as e:
            return {"status": "error", "repo": repo, "pr": pr_id, "error": str(e)}

    def _trigger_workflow(self, repo: str, workflow: str) -> Dict[str, Any]:
        """Trigger a GitHub Action workflow."""
        import requests
        try:
            resp = requests.post(
                f"{self.base_url}/repos/{self.username}/{repo}/actions/workflows/{workflow}/dispatches",
                headers={**self.headers, "Accept": "application/vnd.github.v3+json"},
                json={"ref": "main"},
                timeout=10
            )
            if resp.status_code == 204:
                return {"status": "triggered", "repo": repo, "workflow": workflow}
            else:
                return {"status": "failed", "repo": repo, "workflow": workflow, "error": resp.text}
        except Exception as e:
            return {"status": "error", "repo": repo, "workflow": workflow, "error": str(e)}

# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = GitHubBot()
    result = bot.handle_task({"type": "status"})
    print(f"GitHub status: {result}")

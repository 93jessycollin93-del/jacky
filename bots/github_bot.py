#!/usr/bin/env python3
"""
GitHub Bot - Manages repos, PRs, branches, deployments
Talks to GitHub API (would need token).
Reports back to Jacky.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# bots/ is not a package (no __init__.py / relative-import support), and
# repo_mirror.py lives at the project root, so we add it to sys.path here
# rather than restructuring the bot layout.
from repo_mirror import get_local_repo_path, repo_status  # noqa: E402

log = logging.getLogger("GitHubBot")

class GitHubBot:
    """Jacky's GitHub manager."""

    def __init__(self, token: str = None):
        self.name = "github_bot"
        self.token = token
        # Would initialize GitHub API client here
        log.info("GitHub Bot ready")

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

        if task_type == "status":
            # List all PRs, branches, etc.
            result = {
                "status": "ok",
                "repositories": self._get_repos_status(),
                "prs": self._get_pending_prs(),
                "branches": self._get_stale_branches()
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

        log.info(f"GitHub task {task_type} complete")
        return result

    def _get_repos_status(self) -> List[Dict[str, Any]]:
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

    def _get_pending_prs(self) -> List[Dict[str, Any]]:
        """PRs awaiting review or action."""
        # Would call GitHub API
        return [
            {
                "repo": "cyber-store",
                "number": 42,
                "title": "Integrate Jackie animations",
                "status": "review_needed",
                "age_hours": 3
            }
        ]

    def _get_stale_branches(self) -> List[Dict[str, str]]:
        """Branches that haven't been touched in a while."""
        # Would call GitHub API
        return [
            {"repo": "eru", "branch": "feature/old-feature", "days_since_update": 15}
        ]

    def _merge_pr(self, repo: str, pr_id: int) -> Dict[str, Any]:
        """Merge a PR (with permission)."""
        # Would call GitHub API + require user confirmation
        return {"status": "merged", "repo": repo, "pr": pr_id}

    def _trigger_workflow(self, repo: str, workflow: str) -> Dict[str, Any]:
        """Trigger a GitHub Action workflow."""
        # Would call GitHub API
        return {"status": "triggered", "repo": repo, "workflow": workflow}

# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = GitHubBot()
    result = bot.handle_task({"type": "status"})
    print(f"GitHub status: {result}")

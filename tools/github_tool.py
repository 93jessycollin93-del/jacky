#!/usr/bin/env python3
"""
tools/github_tool.py — Lightweight GitHub REST API helper for OmniAgent.

Requires the GITHUB_TOKEN environment variable (read from secrets_loader or env).
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import request, parse, error

_BASE = "https://api.github.com"
_TOKEN = os.getenv("GITHUB_TOKEN", "")


def _headers() -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "OmniAgent/1.0",
    }
    if _TOKEN:
        h["Authorization"] = "token " + _TOKEN
    return h


def _request(method: str, path: str, body: Any = None) -> Any:
    url = _BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except error.HTTPError as exc:
        raise RuntimeError(
            f"GitHub API {method} {path} → HTTP {exc.code}: {exc.read().decode()}"
        ) from exc


# ── Public helpers ──────────────────────────────────────────────────────────

def get_repo(owner: str, repo: str) -> dict:
    """Return repository metadata."""
    return _request("GET", f"/repos/{owner}/{repo}")


def list_issues(owner: str, repo: str, state: str = "open") -> list[dict]:
    """Return issues for a repository."""
    return _request("GET", f"/repos/{owner}/{repo}/issues?state={state}&per_page=50")


def create_issue(owner: str, repo: str, title: str, body: str = "", labels: list[str] | None = None) -> dict:
    """Open a new issue."""
    payload: dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    return _request("POST", f"/repos/{owner}/{repo}/issues", payload)


def add_comment(owner: str, repo: str, issue_number: int, body: str) -> dict:
    """Post a comment on an issue or PR."""
    return _request(
        "POST",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        {"body": body},
    )


def list_pull_requests(owner: str, repo: str, state: str = "open") -> list[dict]:
    """Return pull requests."""
    return _request("GET", f"/repos/{owner}/{repo}/pulls?state={state}&per_page=50")


def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
    draft: bool = True,
) -> dict:
    """Open a new pull request."""
    return _request(
        "POST",
        f"/repos/{owner}/{repo}/pulls",
        {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "draft": draft,
        },
    )


def get_workflow_runs(owner: str, repo: str, workflow_id: str) -> list[dict]:
    """List recent runs for a workflow."""
    return _request(
        "GET",
        f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?per_page=10",
    ).get("workflow_runs", [])


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python github_tool.py <owner> <repo>")
        sys.exit(1)

    owner, repo = sys.argv[1], sys.argv[2]
    info = get_repo(owner, repo)
    print(f"Repo: {info['full_name']}  ★{info['stargazers_count']}  "
          f"Issues: {info['open_issues_count']}")

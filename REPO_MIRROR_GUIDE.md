# Repo Mirror Guide

How Jacky keeps local copies of every repo in the fleet (condensers, bots,
knowledge sources) so any bot/agent can read them without hitting the
GitHub API every time.

## Why

The old `scripts/clone_all_repos.bat` only worked on Windows, hardcoded a
single machine's drive letter (`E:\superagent\condensers`), and had no way
to tell other parts of Jacky where the mirrors lived. This system replaces
it with something cross-platform, configurable, and discoverable.

## The pieces

| File | Role |
|---|---|
| `repos.json` | Single source of truth: every repo's name, owner, and tag (`condenser`, `bot`, `knowledge-source`, `core`). Edit this file to add/remove repos — don't edit scripts. |
| `scripts/sync_repos.py` | Cross-platform clone/pull script. Reads `repos.json`, mirrors each repo, writes a status report. |
| `repo_mirror.py` | Shared helper module other bots import to find a repo's local path and last sync status. |
| `scripts/clone_all_repos.bat` | Thin Windows wrapper that now just calls `sync_repos.py` (kept for muscle memory / double-click convenience). |

## Usage

```bash
# Sync every repo in repos.json into the default mirror dir (data/repo_mirror/)
python scripts/sync_repos.py

# Use a custom location (e.g. a shared drive other machines also read)
python scripts/sync_repos.py --base-dir /mnt/superagent/condensers
# or, persistently:
export JACKY_REPOS_DIR=/mnt/superagent/condensers
python scripts/sync_repos.py

# Only sync one category of repo
python scripts/sync_repos.py --only condenser,bot

# Preview without touching git or disk
python scripts/sync_repos.py --dry-run
```

Private repos are authenticated using `GITHUB_TOKEN`, resolved through the
existing `secrets_loader.py` precedence chain (env var → `secrets/secrets.env`
→ `.env`). Public repos work with no token at all.

## Where the mirrors live

Resolution order (first match wins):
1. `--base-dir` CLI flag
2. `JACKY_REPOS_DIR` environment variable
3. `base_dir` field in `repos.json`
4. Default: `data/repo_mirror/` (gitignored — never committed)

## Status reporting

After every run, `scripts/sync_repos.py` writes
`data/repo_mirror_status.json`:

```json
{
  "generated_at": "2026-06-30T21:30:00+00:00",
  "total": 40,
  "ok": 38,
  "errors": 2,
  "repos": [
    {"name": "eru", "owner": "93jessycollin93-del", "tag": "knowledge-source",
     "path": "/path/to/data/repo_mirror/eru", "action": "pull",
     "status": "ok", "last_synced": "2026-06-30T21:30:00+00:00", "error": null}
  ]
}
```

## Using mirrors from other bots/agents

Import `repo_mirror.py` instead of re-implementing path resolution:

```python
from repo_mirror import get_local_repo_path, repo_status

path = get_local_repo_path("eru")
if path:
    # read files directly from the local mirror
    ...
else:
    # no local mirror yet — fall back to the GitHub API
    ...
```

`bots/github_bot.py` already does this for its repo-status lookups.

## Scheduling

Run `python scripts/sync_repos.py` on its own schedule, or fold it into the
existing daily routine:

```bash
python daily_workflow.py --sync-repos
```

Cron example (6am daily):

```cron
0 6 * * * cd /path/to/jacky && python daily_workflow.py --sync-repos >> data/repo_sync.log 2>&1
```

## Adding/removing a repo

Edit `repos.json` — add or remove an entry under `"repos"`. No code changes
needed. Optional per-repo fields:
- `"owner"` — overrides `default_owner` for that one repo
- `"path"` — overrides the mirror folder name (defaults to the repo name)

---
name: add-feature
description: End-to-end feature implementation: design → code → test → PR.
version: "1.0"
tools: [read_file, write_file, edit_file, code_search, run_tests, run_terminal, github_api, create_pull_request]
---

# Skill: add-feature

## Purpose
Implement a new feature in the Jacky codebase from requirements to merged PR.

## Parameters
| Name | Required | Description |
|------|----------|-------------|
| `feature` | ✅ | Brief description of the feature |
| `acceptance_criteria` | ✅ | Bullet list of testable criteria |
| `target_files` | ❌ | Known files to modify (agent will discover if omitted) |

## Steps

### 1 — Clarify & Design
- Restate the feature + acceptance criteria in your own words.
- Identify all files that need to change.
- Write a 3–7 step implementation plan.

### 2 — Branch
```bash
run_terminal("git checkout -b feat/<feature-slug>")
```

### 3 — Implement
- Follow `CoderAgent` code standards.
- One logical change per commit.

### 4 — Test
- Write tests before or alongside implementation.
- `run_tests` must be green before opening a PR.

### 5 — PR
```
create_pull_request(
  title="feat: <feature>",
  body="## Summary\n...\n## Acceptance Criteria\n- [ ] ...",
  draft=false
)
```

## Acceptance Criteria
- Feature works as described.
- All existing tests still pass.
- New tests cover the happy path + at least one error path.
- PR has a clear description and links to the originating issue.

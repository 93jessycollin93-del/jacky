# Skills Directory

Reusable skill definitions for OmniAgent. Each `.skill.md` file describes a
repeatable workflow that any agent can invoke.

## Available Skills

| Skill | File | Description |
|-------|------|-------------|
| Web Research | `web-research.skill.md` | Research a topic and return a cited report |
| Code Refactor | `code-refactor.skill.md` | Improve module structure without breaking behaviour |
| Write Tests | `write-tests.skill.md` | Generate comprehensive pytest tests |
| Debug Issue | `debug-issue.skill.md` | Diagnose and fix bugs systematically |

## Skill file format

```yaml
---
skill: skill-name
description: One-line description
version: "1.0"
tools: [tool1, tool2]
inputs:
  - name: param
    description: What this parameter means
outputs:
  - name: result
    description: What the skill returns
---
```

## Subdirectories

| Dir | Purpose |
|-----|---------|
| `scripts/` | Helper scripts used by skills |
| `references/` | Reference docs (copied locally for offline use) |
| `assets/` | Images, diagrams, and other binary assets used by skills |

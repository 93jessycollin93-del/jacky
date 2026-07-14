# Skills Reference Index

This directory contains reusable **skill files** for OmniAgent and its
specialist sub-agents.  Each skill is a self-contained Markdown document with
YAML front-matter metadata and step-by-step instructions.

## Available Skills

| Skill | File | Description |
|-------|------|-------------|
| Web Research | `web-research.skill.md` | Multi-source research → structured report |
| Code Refactor | `code-refactor.skill.md` | Safe incremental refactoring with test guard |
| Add Feature | `add-feature.skill.md` | End-to-end feature: design → code → test → PR |

## Invoking a Skill

```
@OmniAgent run skill: web-research query="vector databases 2025"
@OmniAgent run skill: code-refactor target=jacky_core.py goal="extract router"
@OmniAgent run skill: add-feature feature="healthz endpoint" acceptance_criteria="returns JSON with uptime"
```

## Creating a New Skill

1. Copy the template below into a new file: `<name>.skill.md`
2. Fill in the YAML front-matter (`name`, `description`, `tools`).
3. Define **Parameters**, **Steps**, and **Acceptance Criteria** sections.
4. Add it to the table above.

### Minimal Skill Template

```markdown
---
name: my-skill
description: One-line description.
version: "1.0"
tools: [read_file, run_terminal]
---

# Skill: my-skill

## Purpose
...

## Parameters
| Name | Required | Description |
|------|----------|-------------|
| `param` | ✅ | ... |

## Steps
1. ...

## Acceptance Criteria
- ...
```

## Directory Layout

```
skills/
  *.skill.md        ← skill definitions
  scripts/          ← helper scripts referenced by skills
  references/       ← static reference data (JSON, CSV, etc.)
  assets/           ← diagrams, icons used in skill docs
  SKILLS.md         ← this file
```

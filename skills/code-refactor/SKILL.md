---
name: code-refactor
description: Safely improve code structure while preserving behavior.
version: 1.0.0
inputs:
  - target files or symbols
  - desired outcome
outputs:
  - refactor plan
  - changed files
  - validation evidence
---

# Code Refactor Skill

Use this skill for cleanup, modularization, performance improvements, dependency migration, or design simplification.

## Workflow
1. Read relevant code, tests, and documentation.
2. Identify current behavior and invariants.
3. Make the smallest safe change.
4. Add or update tests only where behavior needs protection.
5. Run existing validation commands.
6. Summarize before/after structure, behavior preservation, and risks.

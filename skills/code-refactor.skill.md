---
name: code-refactor
description: >
  Safely refactor a target file or function toward a stated goal, with tests
  to prove behaviour is preserved.
version: "1.0"
tools: [read_file, edit_file, code_search, run_tests, run_terminal, github_api]
---

# Skill: code-refactor

## Purpose
Incrementally improve code quality (extract, rename, simplify, decouple)
while guaranteeing no behaviour change.

## Parameters
| Name | Required | Description |
|------|----------|-------------|
| `target` | ✅ | File path(s) to refactor |
| `goal` | ✅ | One-sentence description of the desired improvement |
| `test_command` | ❌ | Override default test runner (default: `python -m pytest`) |

## Steps

### 1 — Baseline
```bash
run_tests   # record current pass/fail count
```
If tests fail before refactoring, **stop** and report to the caller.

### 2 — Understand
```
read_file("<target>")
code_search("<key symbols in target>")
```
Map the call graph: who calls this code, what does it depend on?

### 3 — Plan
List the specific refactoring moves you will apply:
- Extract method / function
- Rename for clarity
- Remove dead code
- Introduce abstraction / interface
- Reduce cyclomatic complexity

### 4 — Apply (one move at a time)
For each move:
1. `edit_file` with a surgical replacement.
2. `run_tests` — confirm still green.
3. If red, revert immediately and re-plan.

### 5 — Verify
```bash
run_terminal("python -m pytest --tb=short -q")
run_terminal("flake8 <target> --max-line-length=120")
```

### 6 — Document
Update the docstring / module-level comment to reflect the new structure.

## Acceptance Criteria
- All tests pass after refactoring (same count as baseline).
- Flake8 reports zero new errors.
- Cyclomatic complexity has not increased.
- PR description includes before/after complexity metrics.

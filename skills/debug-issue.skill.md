---
skill: debug-issue
description: Diagnose and fix a bug described by a user report or failing test.
version: "1.0"
tools: [read_file, run_shell, code_search, edit_file, run_tests]
inputs:
  - name: symptom
    description: Description of the bug or failing test output
outputs:
  - name: fix_summary
    description: What the root cause was and what was changed
---

# Skill: Debug Issue

## Purpose

Systematically diagnose and fix a reported bug using the scientific method.

## Steps

1. **Reproduce** — run the failing test or command locally.
2. **Hypothesize** — form 2-3 candidate root causes.
3. **Investigate** — read relevant files; add temporary debug prints if needed.
4. **Isolate** — narrow down to the exact line/function causing the issue.
5. **Fix** — apply the minimal change using `edit_file`.
6. **Verify** — run tests; confirm the symptom is gone.
7. **Clean up** — remove any debug prints added in step 3.

## Chain-of-thought template

```
SYMPTOM: {symptom}
HYPOTHESIS 1: ...  →  INVESTIGATION: ...  →  RESULT: confirmed/ruled out
HYPOTHESIS 2: ...  →  ...
ROOT CAUSE: ...
FIX: {minimal change description}
VERIFICATION: {test result}
```

## Common Jacky-specific pitfalls
- GPU temp returns `None` when `nvidia-smi` is unavailable (Codespace).
- `OLLAMA_HOST` not set → connection refused on port 11434.
- `secrets/secrets.env` not found → `secrets_loader.py` silently skips keys.

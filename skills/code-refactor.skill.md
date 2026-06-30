---
skill: code-refactor
description: Refactor a Python or JS module for clarity, performance, and testability.
version: "1.0"
tools: [read_file, edit_file, run_tests, code_search]
inputs:
  - name: file_path
    description: Path to the file to refactor
  - name: goal
    description: "e.g., 'reduce complexity', 'add type hints', 'extract classes'"
outputs:
  - name: diff_summary
    description: Summary of changes made
---

# Skill: Code Refactor

## Purpose

Improve the internal structure of a module without changing its external behaviour.

## Steps

1. **Read** the target file and understand its purpose.
2. **Identify** refactor targets:
   - Functions > 50 lines → extract sub-functions.
   - Duplicate logic → extract helpers.
   - Magic numbers/strings → named constants.
   - Missing type hints (Python) → add them.
3. **Apply** changes using `edit_file` (surgical replacements only).
4. **Run tests** to confirm no behaviour change.
5. **Report** a bullet-list summary of every change made.

## Rules
- Do NOT change public API signatures (function names, return types).
- Do NOT reformat code that is not being changed (avoid noisy diffs).
- Do NOT introduce new dependencies.

## Verification checklist
- [ ] All existing tests pass after refactor.
- [ ] No new linting errors introduced.
- [ ] Diff is minimal — only the intended changes.

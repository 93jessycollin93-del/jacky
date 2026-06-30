# Safety and Verification

OmniAgent should complete tasks with evidence, not assumptions.

## Required Checks

- Run existing tests, lint, and build commands when relevant.
- Scan changed files for secrets.
- Review dependencies before adding or updating packages.
- Use CodeQL/static analysis for non-trivial code changes when available.
- Include accessibility checks for UI changes.

## Failure Handling

Stop and ask for guidance when requirements conflict, validation is blocked, or a destructive operation is required.

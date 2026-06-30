---
name: security-review
description: Threat model and validate code, dependencies, workflows, and secrets handling.
version: 1.0.0
inputs:
  - changed files
  - runtime context
outputs:
  - findings
  - mitigations
  - verification status
---

# Security Review Skill

Use this skill for authentication, authorization, input parsing, dependency changes, CI/CD, cloud credentials, web exposure, and any code handling untrusted input.

## Workflow
1. Identify assets, trust boundaries, entry points, and threat actors.
2. Check secrets handling and logging.
3. Review dependencies and workflow permissions.
4. Validate input sanitization, output encoding, and error handling.
5. Record accepted risks and required follow-up.

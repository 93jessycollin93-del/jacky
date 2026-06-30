---
name: web-research
description: Research current external information with citations and confidence levels.
version: 1.0.0
inputs:
  - research question
  - constraints
outputs:
  - cited findings
  - recommendation
  - risks and unknowns
---

# Web Research Skill

Use this skill when a task requires current documentation, standards, release information, vendor behavior, or comparison across external sources.

## Workflow
1. Restate the research question and acceptance criteria.
2. Prefer primary sources and official documentation.
3. Cross-check important claims with at least two sources when possible.
4. Record source title, URL, date accessed, and relevance.
5. Summarize findings, confidence, risks, and next action.

## Verification
- Mark stale or conflicting sources.
- Separate facts from recommendations.
- Do not expose private repository content to third-party services.

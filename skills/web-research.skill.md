---
name: web-research
description: Deep-dive web research for a query; produces a structured Markdown report.
version: "1.0"
tools: [web_search, web_fetch, write_file]
output: docs/<slug>_research.md
---

# Skill: web-research

## Purpose
Perform multi-source web research on a topic and produce a structured report.

## Parameters
| Name | Required | Description |
|------|----------|-------------|
| `query` | ✅ | The research question or topic |
| `depth` | ❌ | `shallow` (3 sources) or `deep` (8+ sources, default: `deep`) |
| `output_file` | ❌ | Override the default output path |

## Steps

### 1 — Decompose the query
Break `query` into 3–5 atomic sub-questions.

### 2 — Search
For each sub-question:
```
web_search("<sub-question> site:docs.* OR github.com OR arxiv.org")
```
Collect the top 2 URLs per sub-question.

### 3 — Fetch
```
web_fetch("<url>")   # repeat for each collected URL
```
Extract the relevant sections.

### 4 — Synthesise
- Cross-reference findings.
- Note contradictions and knowledge gaps.
- Build a comparison table if the question is evaluative (A vs B vs C).

### 5 — Write report
Save to `output_file` using this template:

```markdown
# Research Report: <query>
Generated: <ISO date>

## Executive Summary
<!-- 3 sentences max -->

## Findings

### <Sub-question 1>
...

### <Sub-question N>
...

## Comparison Table (if applicable)
| Criterion | Option A | Option B |
|-----------|----------|----------|

## Recommendations
1. ...

## Sources
- [Title](URL) — accessed <date>
```

## Acceptance Criteria
- Report file created at `output_file`.
- Minimum 3 unique sources cited (8 for `depth=deep`).
- No `[UNVERIFIED]` claims left without a note.
- Report passes Markdown lint.

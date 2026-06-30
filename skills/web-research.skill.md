---
skill: web-research
description: Systematically research a topic on the web and return a structured report.
version: "1.0"
tools: [web_fetch, code_search]
inputs:
  - name: topic
    description: The topic or question to research
  - name: depth
    description: "shallow | deep (default: shallow)"
outputs:
  - name: report
    description: Markdown report with findings and citations
---

# Skill: Web Research

## Purpose

Given a topic, search the web for relevant documentation, GitHub issues, and
community resources. Return a structured markdown report.

## Steps

1. **Decompose** the topic into 3-5 targeted search queries.
2. **Fetch** each URL using `web_fetch`.
3. **Extract** the most relevant 200-500 words per source.
4. **Synthesize** findings into a single coherent narrative.
5. **Cite** every claim with `[title](url)`.

## Output template

```markdown
## Research Report: {topic}

### Key Findings
- Finding 1 [source](url)
- Finding 2 [source](url)

### Recommendations
1. ...
2. ...

### Sources
| Title | URL | Relevance |
|-------|-----|-----------|
```

## Quality checks
- [ ] All facts have citations.
- [ ] No contradictory claims without noting the contradiction.
- [ ] Recommendations are actionable.

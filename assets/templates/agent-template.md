# Agent Definition Template

Copy this file to `.github/agents/my-agent.agent.md` and fill in the blanks.

```markdown
---
name: MyAgent
description: One sentence describing what this agent does.
version: "1.0"
model: claude-haiku   # cheapest capable model first
tools:
  - read_file
  - write_file
  # add more as needed
---

# MyAgent

## Persona
[Describe the agent's role and expertise in 2-3 sentences.]

## Responsibilities
- [Primary responsibility]
- [Secondary responsibility]

## Workflow
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Rules
- [Constraint 1]
- [Constraint 2]

## Verification checklist
- [ ] [Check 1]
- [ ] [Check 2]
```

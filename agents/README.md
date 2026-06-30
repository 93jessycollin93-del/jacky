# Agents Directory

This directory contains human-readable reference cards for each OmniAgent
sub-agent. The canonical agent definitions live in `.github/agents/`.

| File | Agent | Role |
|------|-------|------|
| `coder.md` | CoderAgent | Write, refactor, and debug code |
| `researcher.md` | ResearcherAgent | Web research and codebase search |
| `tester.md` | TesterAgent | Write and run tests |
| `devops.md` | DevOpsAgent | CI/CD, Docker, infrastructure |
| `reviewer.md` | ReviewerAgent | PR review and security audit |

## Invoking an agent (Copilot Chat)

```
@workspace /agent coder Fix the thermal gating logic in situation_assessor.py
@workspace /agent researcher Find best practices for Ollama streaming responses
@workspace /agent tester Write tests for cloud_router.py
```

## Adding a new agent

1. Create `.github/agents/my-agent.agent.md` with YAML frontmatter + instructions.
2. Add a reference card here in `agents/my-agent.md`.
3. Register the agent in `assets/templates/agent-template.md` if needed.

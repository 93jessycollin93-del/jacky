# OmniAgent Documentation

OmniAgent is the GitHub Copilot-native AI orchestration layer built on top of Jacky.
It gives Jacky a rich set of specialized agents, reusable skills, and structured
reasoning patterns accessible from Copilot Chat and CI/CD workflows.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Agents](#agents)
4. [Skills](#skills)
5. [Prompt Templates](#prompt-templates)
6. [CI/CD Integration](#cicd-integration)
7. [Adding New Agents](#adding-new-agents)
8. [Adding New Skills](#adding-new-skills)
9. [Troubleshooting](#troubleshooting)

---

## Overview

OmniAgent layers on top of Jacky's existing routing engine to provide:

- **5 specialized sub-agents** (Coder, Researcher, Tester, DevOps, Reviewer)
- **4 reusable skills** (Web Research, Code Refactor, Write Tests, Debug Issue)
- **Prompt library** with ReAct, Plan-and-Execute, and CoT templates
- **CI workflow** that validates all agent definition files on every PR

---

## Architecture

See `assets/diagrams/architecture.md` for the full diagram.

The core routing hierarchy:

```
User → OmniAgent → [sub-agent] → [skill] → [tool] → [AI model]
```

AI model selection (cheapest first):
1. Local Ollama (thermal-gated at 70 °C)
2. Groq (free tier)
3. Gemini Flash (free tier)
4. OpenRouter (free tier)
5. Claude Haiku (paid fallback)

---

## Agents

| Agent | File | Best for |
|-------|------|----------|
| OmniAgent | `.github/agents/OmniAgent.agent.md` | Master orchestrator |
| CoderAgent | `.github/agents/coder.agent.md` | Implementation tasks |
| ResearcherAgent | `.github/agents/researcher.agent.md` | Documentation & research |
| TesterAgent | `.github/agents/tester.agent.md` | Test generation |
| DevOpsAgent | `.github/agents/devops.agent.md` | CI/CD & infrastructure |
| ReviewerAgent | `.github/agents/reviewer.agent.md` | Code review |

### Invoking in Copilot Chat

```
@workspace /agent OmniAgent Refactor cloud_router.py to support streaming
@workspace /agent coder Fix the TypeError in situation_assessor.py line 42
@workspace /agent tester Generate tests for jacky_core.py
```

---

## Skills

| Skill | File |
|-------|------|
| Web Research | `skills/web-research.skill.md` |
| Code Refactor | `skills/code-refactor.skill.md` |
| Write Tests | `skills/write-tests.skill.md` |
| Debug Issue | `skills/debug-issue.skill.md` |

Skills are invoked automatically by agents or can be called explicitly:

```
@workspace /skill web-research topic="Ollama quantization formats"
```

---

## Prompt Templates

See `assets/prompts/prompt-library.md` for:

- Plan-and-Execute bootstrap
- Code review request
- Bug report → investigation
- Thermal-aware routing
- Chain-of-thought verification

---

## CI/CD Integration

`.github/workflows/omniagent-ci.yml` runs on every PR and push:

1. **OmniAgent Tests** — runs `pytest tests/omniagent/`
2. **Validate Agent Definitions** — checks every `.agent.md` has valid frontmatter

---

## Adding New Agents

1. Copy `assets/templates/agent-template.md` to `.github/agents/my-agent.agent.md`.
2. Fill in the YAML frontmatter (name, description, model, tools).
3. Write the system prompt in the markdown body.
4. Add a row in `agents/README.md`.
5. The CI workflow will automatically validate your new file.

---

## Adding New Skills

1. Copy `assets/templates/skill-template.md` to `skills/my-skill.skill.md`.
2. Fill in frontmatter and workflow steps.
3. Add a row in `skills/SKILLS.md`.

---

## Troubleshooting

**Agent not found in Copilot Chat**
- Make sure the file is in `.github/agents/` and named `*.agent.md`.
- Confirm the YAML frontmatter `name:` field matches what you're typing.

**CI workflow failing on frontmatter validation**
- Run `python -c "import yaml; yaml.safe_load(open('.github/agents/my-agent.agent.md').read().split('---',2)[1])"` locally.

**Skill inputs not substituted**
- Check the placeholder format is `{input_name}` (single curly braces).
- Verify the key name matches exactly (case-sensitive).

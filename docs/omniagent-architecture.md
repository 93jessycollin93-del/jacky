# OmniAgent Architecture

## Overview

OmniAgent is the top-level autonomous agent that orchestrates all tasks within
the **Jacky** AI platform.  It delegates to specialist sub-agents, invokes
reusable skills, and uses the Model Context Protocol (MCP) to extend its tool
set dynamically.

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Copilot / VS Code                 │
│                    (user invokes @OmniAgent)                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          OmniAgent                              │
│   .github/agents/omniagent.agent.md                             │
│                                                                 │
│   Reasoning: ReAct → Plan-and-Execute → Tree-of-Thoughts        │
│   Tools: file_ops, code_search, shell, web, github, mcp         │
└──────┬──────────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
  CoderAgent  Researcher  Tester   DevOps   Accessibility
  Agent       Agent       Agent    Agent    Agent
       │          │          │          │          │
       └──────────┴──────────┴──────────┴──────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Skills System      │
                    │   skills/*.skill.md  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   MCP Server         │
                    │   jacky-mcp-server   │
                    └──────────┬───────────┘
                               │
                  ┌────────────┼────────────┐
                  ▼            ▼            ▼
            Jacky Core   Situation    Cloud Router
            (routing)    Assessor     (Groq→Gemini
                         (thermals)    →Claude)
```

---

## Directory Structure

```
jacky/
├── .github/
│   ├── agents/
│   │   └── omniagent.agent.md      ← Main agent definition
│   └── workflows/
│       └── agent-tasks.yml         ← CI/CD + agent trigger
│
├── agents/                         ← Specialist sub-agents
│   ├── coder.agent.md
│   ├── researcher.agent.md
│   ├── tester.agent.md
│   ├── devops.agent.md
│   └── accessibility.agent.md
│
├── skills/                         ← Reusable skill definitions
│   ├── web-research.skill.md
│   ├── code-refactor.skill.md
│   ├── add-feature.skill.md
│   ├── scripts/                    ← Helper scripts for skills
│   ├── references/                 ← Static reference data
│   └── assets/                     ← Diagrams, icons
│
├── tools/                          ← Tool implementations
│   ├── file_ops.py
│   ├── github_tool.py
│   └── shell_tool.py
│
├── mcp-servers/                    ← MCP server configs & code
│   ├── mcp-config.json
│   └── jacky_mcp_server.py
│
├── assets/
│   ├── templates/                  ← task-template, pr-template
│   ├── prompts/                    ← ReAct, CoT frameworks
│   └── diagrams/
│
├── examples/                       ← Runnable usage examples
├── tests/
│   └── agent_tests/                ← Tests for agent tools
│
├── jacky_core.py                   ← Jacky orchestrator
├── situation_assessor.py           ← GPU/CPU thermal gating
├── cloud_router.py                 ← Groq → Gemini → Claude
├── jacky_api.py                    ← Flask dev server
└── serve.py                        ← Production WSGI (Waitress)
```

---

## Routing Decision Tree

```
Task received
     │
     ▼
GPU temp < 70°C?
  ├─ YES → Try Ollama (local)
  │          └─ Success? → Return response
  │          └─ Fail/timeout → fall through
  └─ NO  → Skip local
     │
     ▼
Free cloud available?
  ├─ YES → Try Groq (fastest free)
  │          └─ Success? → Return
  │          └─ Fail → Try Gemini
  │                      └─ Success? → Return
  │                      └─ Fail → fall through
  └─ NO  → fall through
     │
     ▼
Paid cloud (Claude Haiku)
     └─ Return response (or raise if no API key)
```

---

## Security Model

| Concern | Mitigation |
|---------|-----------|
| Secrets in code | `secrets_loader.py` + `.gitignore` for `secrets/` |
| Path traversal | `file_ops._safe_path()` enforces repo root boundary |
| Shell injection | `shell_tool` uses `shlex.split` + allowlist |
| API key exposure | `github_tool.py` never logs tokens |
| Runaway costs | `max_cost_tier` parameter on every routing call |
| Thermal damage | `SituationAssessor` hard-stops at 75°C |

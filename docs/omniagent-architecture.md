# OmniAgent Architecture

OmniAgent is organized as a modular agent starter kit layered on top of this repository.

## Layers

1. **Main agent definition** — `.github/agents/OmniAgent.agent.md` defines persona, protocol, safety, and tool categories.
2. **Role agents** — `agents/*.agent.md` describe focused modes for coding, research, testing, DevOps, and accessibility.
3. **Skills** — `skills/*/SKILL.md` package reusable workflows with scripts, references, and assets.
4. **Tools and MCP** — `tools/` contains sample custom tools; `mcp-servers/` contains extension server configuration.
5. **Assets** — templates, prompt patterns, diagrams, and icons used by agents and humans.
6. **Verification** — `tests/` and `.github/workflows/` ensure the starter kit remains coherent.

## Execution Loop

Plan, select skill or role, use tools, verify, reflect, and report. This structure keeps prompts small while making capabilities discoverable and extensible.

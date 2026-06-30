# Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────┐
│                     USER / SAS DASHBOARD                │
└──────────────────────────┬──────────────────────────────┘
                           │ request
                           ▼
┌─────────────────────────────────────────────────────────┐
│                       OmniAgent                         │
│  (ReAct reasoning · Plan-and-Execute · self-healing)    │
│                                                         │
│  ┌──────────┐  ┌────────────┐  ┌──────────┐            │
│  │  Planner │  │ Tool Router│  │ Verifier │            │
│  └──────────┘  └──────┬─────┘  └──────────┘            │
└──────────────────────┬┴────────────────────────────────┘
                       │ delegates
          ┌────────────┼────────────┬─────────────┐
          ▼            ▼            ▼             ▼
   ┌────────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐
   │CoderAgent  │ │Researcher│ │Tester  │ │DevOps    │
   └──────┬─────┘ └────┬─────┘ └───┬────┘ └────┬─────┘
          │             │           │            │
          ▼             ▼           ▼            ▼
   ┌─────────────────────────────────────────────────────┐
   │                    Tool Layer                       │
   │  file_ops · shell · web_fetch · github_api ·       │
   │  jacky_api · ollama_client · mcp_servers           │
   └─────────────────────────────────────────────────────┘
          │
          ▼
   ┌──────────────────────────────────────────────────────┐
   │              AI Routing (economy-first)              │
   │  Local Ollama → Groq (free) → Gemini (free)         │
   │  → OpenRouter (free tier) → Claude Haiku (paid)     │
   └──────────────────────────────────────────────────────┘
```

## Key design principles

1. **Local-first** — Ollama models run on the physical PC (RTX 3090).
2. **Thermal gating** — GPU ≥ 70 °C → route to small/free models.
3. **Economy mode** — cheapest capable model wins.
4. **Sub-agent delegation** — OmniAgent never does everything itself.
5. **Skills as composable workflows** — agents invoke skills, not raw prompts.

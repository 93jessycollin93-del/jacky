# Jacky — AI Operations Manager

**Owner:** eru (93jessycollin93-del on GitHub)  
**Stack:** Python 3.11, Flask/Waitress, Ollama (local), Claude Haiku (cloud fallback)

## What this project is

Jacky is a situation-aware AI orchestration engine that:
- Routes tasks to the cheapest capable AI (local Ollama → free cloud → paid cloud)
- Monitors GPU thermals (RTX 3090, hard stop at 75°C) and CPU/RAM pressure
- Serves a secure web dashboard (SAS) accessible from phone via Cloudflare tunnel
- Manages a fleet of local Ollama models + 2 named cloud bots (jacky/Gemini, claude_jr/Haiku)

## Key files

| File | Role |
|---|---|
| `jacky_core.py` | Main orchestrator — task routing, bot management |
| `situation_assessor.py` | Reads GPU temp, CPU/RAM, decides local vs cloud |
| `cloud_router.py` | Waterfall: Groq → Gemini → OpenRouter → Claude Haiku |
| `serve.py` | Production WSGI server (use this, not jacky_api.py, for internet) |
| `jacky_api.py` | Flask API (dev mode) |
| `config.json` | All tunables — thermal limits, resource caps, preferences |
| `superstation/` | Fleet contract + kernel — see `superstation/README.md` |
| `station.pod.json` | This pod's capability manifest |
| `secrets/secrets.env` | API keys + SAS token (gitignored — never commit) |
| `bots/monitor_bot.py` | System monitor bot |
| `bots/github_bot.py` | GitHub automation bot |

## Running locally

```bash
# Start API server (dev)
python jacky_api.py

# Production server (for internet / SAS dashboard)
python serve.py

# Run efficiency check
python efficiency_check.py
```

## Environment variables needed

```
ANTHROPIC_API_KEY=     # Claude API key (for claude_jr cloud bot)
GEMINI_API_KEY=        # Free Gemini (jacky cloud bot)
GROQ_API_KEY=          # Free Groq (first fallback)
SAS_ACCESS_TOKEN=      # SAS dashboard login token
```

## Architecture notes

- **Local-first**: always tries Ollama models first (thermally gated)
- **Economy mode**: `config.json → preferences.time_cost_preference = "economy"`
- **Thermal gating**: if GPU ≥ 70°C, routes to small models or free cloud
- **Codespace caveat**: Ollama runs on the physical PC, not here. In Codespace,
  point `OLLAMA_HOST=http://your-pc-ip:11434` if you want local model access,
  or the cloud router will handle all inference automatically.

## The Superstation foundation

`superstation/` is the contract the whole fleet shares — nine repos, four stacks,
no common dependency. It is not a library to import so much as a set of rules
with two reference implementations (TypeScript and Python) that are held in sync
by one shared vector file.

The load-bearing idea: **the engine is usually unreachable**, so every value that
crosses a pod boundary carries a provenance block saying how real it is
(`live > cached > degraded > simulated > absent`). A pod cannot emit a reading
without answering that question, and `derive()` carries the weakest input
fidelity into any value computed from it — so a chain of pods cannot launder a
simulated number into a live one.

```bash
python3 superstation/conformance/test_conformance.py   # 71 cases, python kernel
node    superstation/conformance/conformance.mjs       # same 71, typescript kernel
python3 superstation/tools/station_doctor.py .         # validate station.pod.json
python3 superstation/tools/station_sync.py --check-all ..   # vendored-copy drift
```

Read `superstation/SPEC.md` before changing anything under `superstation/` — it
is normative, and the version compatibility rules in §5 are what let one repo
upgrade without the other eight.

## What was last worked on (2026-06-28)

- SAS v2 internet-accessible PWA with token auth + Cloudflare tunnel ✅
- SAS Power Panel with mode presets ✅
- Model downloads in progress on local machine (deepseek-r1:14b, gpt-oss:20b pending)
- Free cloud tier keys (Groq/Gemini/OpenRouter) still need real values in secrets vault
- Permanent sas.cybernetic67.com tunnel not set up yet (needs Cloudflare browser login)

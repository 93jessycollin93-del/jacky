# JACKY - AI Operations Manager
## Architecture & Design

**Version:** 1.1 (Situation-Aware Engine)  
**Purpose:** Manage your PC, projects, and assets. Educate you on systems & security.  
**Frame:** "It's Jacky's PC. You learn from Jacky."

> **v1.1 changes (simplified engine):** primary = local Ollama (thermally gated),
> backup = two named cloud bots (`jacky`/Gemini, `claude_jr`/Haiku), with a free
> escalation tier (Groq → Gemini → OpenRouter) as the safety net. Removed cruft:
> `johnny_ai`, `onslaught_ai`, and the xAI paid backup. See **AI Engine** below —
> it is the authoritative description of what actually runs; the conceptual
> sections further down (decision engine, educator) remain aspirational.

---

## AI Engine: Situation-Aware Routing (v1.1)

This is the live, implemented path behind `POST /api/ask`. The engine is
**local-first and free**, but it never cooks the GPU: a situation assessment runs
*before* anything executes and decides whether local is wise right now.

### Request flow / fallback chain

```
POST /api/ask {prompt, task_type}
        │
        ▼
  SituationAssessor.assess()   ──►  {level, safe_to_run_local, temp, load, vram, reason}
        │
        ▼
  ┌─ safe_for_local AND task isn't complexity-escalated? ─┐
  │                                                       │
  ▼ yes                                                   ▼ no / unsafe
 (1) LOCAL  ollama_ensemble.query_best()        (skip local)
     ok ─► return                                        │
     escalate/error ───────────────────────────────────►│
                                                         ▼
                                            (2) CLOUD  free tier
                                                cloud_router.ask()
                                                Groq → Gemini → OpenRouter
                                                ok ─► return
                                                exhausted/disabled ─┐
                                                                    ▼
                                            (3) FORCED LOCAL (last resort,
                                                ignores thermal — better a
                                                warm GPU than no answer)
                                                ok ─► return
                                                error ─┐
                                                       ▼
                                            (4) ERROR with explanation
                                                + full fallback_chain
```

Every `/api/ask` response carries `assessment`, `why` (the chosen route's
reason), and `fallback_chain` (every step + status), so the dashboard can show
*what ran and why*.

### Situation assessment logic (`situation_assessor.py`)

Combines CPU%, GPU (temp / load / free VRAM), and RAM into one verdict:

```
gpu_temp >= gpu_max_temp_c            → escalate_to_free   (too hot)
gpu_mem_free < task_needs_mb          → escalate_to_free   (VRAM starved)
ram% >= ram_high_percent              → escalate_to_free   (system under pressure)
gpu_temp >= max - thermal_margin      → safe_for_light_cloud (warm: small model / cloud)
gpu_load >= gpu_load_high_percent     → safe_for_light_cloud (busy: small model / cloud)
else                                  → safe_for_local
```

Dashboard badge mapping: `safe_for_local → Safe`, `safe_for_light_cloud → Warm`,
`escalate_* → Escalate`. If `nvidia-smi` is unavailable, the engine falls back to
CPU/RAM only and stays local while calm (it never *blocks* on missing GPU
telemetry).

### Thermal limits — and why they exist (`config.json → gpu_thermal`)

```json
"gpu_thermal": {
  "gpu_max_temp_c": 75,        // hard stop for local work (RTX 3090)
  "thermal_margin": 5,         // within 5°C of max = back off (>=70°C)
  "gpu_load_high_percent": 85  // utilization that counts as "busy"
}
```

- **Why 75°C / 5°C margin?** Keeps the GPU comfortably below throttle and gives
  the assessor a buffer to step aside *before* temps spike, rather than reacting
  after the card is already hot. This is deliberate, calm management — **no
  thermal freakouts**.
- **`resource_policy.ollama_threads_for_thermal()`** halves the Ollama thread
  budget when headroom ≤ margin, so we stop *adding* heat while the card cools.
- **Separate concern — the 980 Pro NVMe:** the SSD (not the GPU) throttles under
  heavy *sustained I/O*. That is handled by loading models **sequentially**
  (`ollama_ensemble.query_ensemble`), not by these temperatures. Don't conflate
  the two: GPU temp gates compute; sequential loads protect the SSD.

### Model selection (`ollama_ensemble.py`)

1. Roster is built live from `nvidia`-pulled models (`/api/tags`), each tagged
   with a specialty (code → `qwen2.5-coder`, reasoning → `qwen3`/`deepseek-r1`,
   security → `whiterabbitneo`, general → `dolphin`/`gpt-oss`, embeddings →
   `nomic-embed`).
2. `task_type` maps to the best-fit specialty.
3. **Thermal gate:** when the assessment is `safe_for_light_cloud` (warm/busy),
   `pick_model(prefer_small=True)` chooses the smallest/fastest pulled model to
   finish quickly and shed less heat. When unsafe, `query_best` returns
   `status="escalate"` *without running* so the API hands off to the free tier.

### Named cloud bots + free escalation tier

- **Named bots** (`config.json → named_cloud_bots`, `bot_router.py`): `jacky`
  (Gemini, free) and `claude_jr` (Claude Haiku, cheap). `bot_router.route()`
  encodes *task-complexity* escalation only (e.g. `strategy → jacky`,
  `debug/analysis → claude_jr`); thermal escalation is decided upstream by the
  assessor.
- **Free tier** (`config.json → integrations.cloud_bots`, `cloud_router.py`):
  Groq → Gemini → OpenRouter, tried in order, first success wins. This is the
  *safety net*, not the primary. Keys load lazily via the gitignored vault
  (`secrets_loader.py`) — **untouched by this engine work**.

### File map

| File | Role |
|------|------|
| `situation_assessor.py` | **(new)** CPU/GPU/RAM → routing verdict + badge |
| `resource_policy.py` | CPU cap **+ GPU thermal** (`gpu_temp`, `gpu_safe_to_use`, `ollama_threads_for_thermal`) |
| `ollama_ensemble.py` | live model roster, thermal-aware `pick_model`/`query_best`, `assess_situation` |
| `bot_router.py` | local-vs-named-bot task routing (jacky, claude_jr only) |
| `cloud_router.py` | free escalation tier (Groq → Gemini → OpenRouter) |
| `jacky_api.py` | `/api/ask` chain, `/api/assessment`, `/api/bots`, `/api/status` (GPU) |
| `sas_ui/dashboard.html` | live badge, GPU thermal card, chosen model + why + chain |
| `config.json` | `gpu_thermal`, `situation_assessment`, `named_cloud_bots` |

### Troubleshooting — "GPU too hot" / requests escalating

- **Symptom:** dashboard badge shows **Escalate**; `/api/ask` returns
  `engine: cloud` (or errors with `forced_local`), `why` mentions temp ≥ max.
- **It's working as designed** — the engine is protecting the card. Check the
  GPU Thermal card: if temp ≥ 75°C, let it cool; requests resume locally once
  headroom returns.
- **Always escalating even when cool?** Verify `nvidia-smi` is on PATH
  (`nvidia-smi --query-gpu=temperature.gpu --format=csv`); if it's missing the
  assessor uses CPU/RAM only. Check `config.json → gpu_thermal` wasn't set too
  low. Check VRAM isn't pinned by another process (free < task need → escalate).
- **Want more local headroom?** Raise `gpu_max_temp_c` (cautiously) or lower
  `gpu_load_high_percent` sensitivity in `config.json`.
- **Escalates but cloud fails too** (`fallback_chain` shows `cloud_free:disabled`
  or `:exhausted`): set `integrations.cloud_bots.enabled: true` and add free
  provider keys to the vault. With cloud off, the engine still answers via
  **forced local** as a last resort.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    JACKY CORE                           │
│           (Python Service on E:\AI\Jacky)               │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Task Analyzer & Router                          │   │
│  │ (decides what work is needed, urgency, scope)   │   │
│  └─────────────────────────────────────────────────┘   │
│                      │                                  │
│  ┌──────────────────┴──────────────────┐               │
│  │                                     │               │
│  ▼                                     ▼               │
│ ┌──────────────────────┐    ┌──────────────────────┐  │
│ │ Resource Manager     │    │ Bot Orchestrator     │  │
│ │ (GPU, RAM, CPU,      │    │ (spawn/manage bots)  │  │
│ │ network, disk)       │    │                      │  │
│ └──────────────────────┘    └──────────────────────┘  │
│                      │                                  │
│                      ▼                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ BOT POOL (configurable, dynamic)                │   │
│  │                                                 │   │
│  │  🤖 GitHub Bot      (PRs, branches, deploys)   │   │
│  │  🤖 Monitor Bot     (system health, alerts)    │   │
│  │  🤖 Security Bot    (perms, vulns, audit)      │   │
│  │  🤖 File Mgr Bot    (storage, cleanup)         │   │
│  │  🤖 Model Bot       (downloads, GPU alloc)     │   │
│  │  🤖 Executor Bot    (runs agents, tests)       │   │
│  │  [Custom bots - user extensible]               │   │
│  └─────────────────────────────────────────────────┘   │
│                      │                                  │
│  ┌──────────────────┴──────────────────┐               │
│  │                                     │               │
│  ▼                                     ▼               │
│ ┌──────────────────────┐    ┌──────────────────────┐  │
│ │ Data Store           │    │ Decision Engine      │  │
│ │ (state, logs,        │    │ (ML/reasoning about  │  │
│ │ metrics, config)     │    │ efficiency, advice)  │  │
│ └──────────────────────┘    └──────────────────────┘  │
│                      │                                  │
│                      ▼                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Alert & Education Engine                        │   │
│  │ (notifies you, explains why, teaches concepts)  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    ┌────────┐  ┌──────────┐  ┌──────────┐
    │  SAS   │  │  REST    │  │ External │
    │   UI   │  │   API    │  │ Integrations
    └────────┘  └──────────┘  └──────────┘
    (dashboard) (apps talk     (GitHub,
                 to Jacky)     file sys)
```

---

## Core Components

### 1. **Jacky Core Service** (`jacky_core.py`)
- Orchestrates all bots
- Analyzes incoming tasks
- Routes to appropriate bot(s)
- Tracks metrics (time, resource use, cost)
- Makes decisions (1 bot? 5 bots in parallel?)

### 2. **Bot System** (`bots/`)
Each bot:
- Has a fixed responsibility
- Listens for tasks routed to it
- Reports status/results back
- Pluggable (you can add `custom_bot.py`)

**Local automation bots** (`config.json → enabled_bots`, files in `bots/`):
- `github_bot.py` — manage GitHub (PRs, branches, workflows)
- `monitor_bot.py` — system health (GPU, RAM, disk, processes)

> Security monitoring is handled **separately by the user**, so `security_bot`
> is not started here. The two *named cloud bots* (`jacky`, `claude_jr`) are a
> different concept — AI backends for escalation, not local automation. See the
> **AI Engine** section above.

### 3. **SAS Dashboard** (`sas_ui/`)
- Web UI (Flask/React or simple HTML)
- Real-time status of everything
- Alerts/warnings prominent
- Shows what needs your attention NOW
- Historical trends

### 4. **Data Store** (`data/`)
- SQLite or JSON-based state
- Logs (what happened when)
- Metrics (time/cost/efficiency tracking)
- Configuration (bot settings, constraints)

### 5. **Decision Engine** (`decision_engine.py`)
- Analyzes tasks + constraints
- Decides optimal bot count
- Estimates time/cost/resource
- Learns from past decisions
- Gives you advice

### 6. **Education Module** (`educator.py`)
- Explains what's happening in plain English
- Teaches concepts (e.g., "why I'm using 3 bots here")
- Alerts include learning snippets
- Grows your knowledge over time

---

## Workflow Example

**User opens SAS dashboard → sees: "GPU at 85%, model download in progress"**

1. Jacky monitors GPU → Alert triggered
2. Monitor Bot checks system state
3. Decision Engine: "GPU is fine, within normal range. No action needed."
4. Education Module explains: "GPUs run hot during intensive tasks. 85% is healthy. If it hits 95%, I'll pause non-essential work."
5. SAS shows: ✅ All good (explanation included)

**Later: User's GitHub PR needs tests run + merged + deployed**

1. Task Router sees: "Run tests (30s) + merge (2s) + deploy (60s) = 92s serial"
2. Resource Manager: "3 bots in parallel = 35s total. Cost: higher GPU use. Worth it."
3. Decision Engine: "Spawn GitHub Bot + Executor Bot + Monitor Bot (watching for failures)"
4. Bots run in parallel
5. SAS shows: Progress bars for each bot
6. Education: "Why I parallelized: your PC has resources. Serial would waste time."

---

## Security Model

- **Permission tiers:** what each bot can access/do
- **Rate limits:** don't hammer GitHub API or file system
- **Audit log:** every action logged with timestamp, bot, user approval
- **Sandboxing:** bots run in isolated contexts (can't break each other)
- **Alerts:** suspicious activity → notify you immediately

---

## Configuration

**User can set:**
- Max bots running at once (default: 4)
- Resource limits per bot (CPU %, RAM, disk I/O)
- Time/cost trade-offs ("prefer speed" vs "minimize cost")
- Which bots to load (enable/disable)
- Custom constraints

---

## Extensibility

**Adding a custom bot:**
```python
# E:\AI\Jacky\bots\my_custom_bot.py
class MyCustomBot:
    def __init__(self):
        self.name = "my_custom_bot"
    def handle_task(self, task):
        # Do your thing
        return result
```

Jacky auto-discovers it and includes it in the pool.

---

## Implementation Timeline

**Phase 1 (MVP):** Core orchestrator + 3 starter bots + basic SAS + local monitoring  
**Phase 2:** GitHub integration + decision engine + education  
**Phase 3:** Advanced security, multi-bot coordination, learning from past decisions  
**Phase 4:** Cloud integrations, advanced analytics  

---

**Frame:** It's Jacky's PC. You're learning from Jacky. Jacky keeps everything running.

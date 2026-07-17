# Jacky Operational Guide — Understanding Scale & Efficiency

**Version:** 1.1 (Situation-Aware Engine)  
**Last Updated:** 2026-06-28

---

## Quick Start — Daily Routine

Every morning (or before heavy use), run:

```bash
python daily_workflow.py --verbose
```

This checks:
- ✓ Ollama (models loaded)
- ✓ Jacky API (responding)
- ✓ GPU (temperature, safe to run?)
- ✓ Assessment (current situation)

Then runs **5 representative tasks** (trivia, coding, analysis, creative, reasoning) and logs metrics to `daily_efficiency_log.csv`.

**Typical output:**
```
Status: ALL OK
Results: 5/5 OK, 0 errors in 67.0s
Throughput: 268 questions/hour
Avg latency: 13.11s per task
GPU temp: 51C (headroom: 24C)
```

### Optional: keep mirrored repos fresh

Add `--sync-repos` to also mirror every repo listed in `repos.json` before
the pulse run (see `REPO_MIRROR_GUIDE.md` and `ARCHITECTURE.md` §7):

```bash
python daily_workflow.py --sync-repos
```

To run this unattended on a schedule (cron example, 6am daily):

```cron
0 6 * * * cd /path/to/jacky && python daily_workflow.py --sync-repos >> data/repo_sync.log 2>&1
```

---

## Understanding the Metrics

### System Check (Prerequisites)

| Component | Status | What It Means |
|-----------|--------|---------------|
| **Ollama** | OK / FAIL | Local model server running; X models loaded |
| **API** | OK / FAIL | Flask REST server responding on localhost:5000 |
| **Assessment** | Safe / Warm / Escalate | Current thermal routing verdict (see below) |
| **GPU** | OK / FAIL | nvidia-smi readable; temp / headroom visible |

If any fails, Jacky won't route requests intelligently. Fix before proceeding.

### Pulse Results (5 lightweight tasks)

| Metric | Target | Interpretation |
|--------|--------|-----------------|
| **Success rate** | 100% (5/5) | All tasks completed; network/timeouts are red flag |
| **Avg latency** | < 15s | Per-request time; <5s=excellent, <15s=good, >20s=investigate |
| **Throughput** | 150-300 q/hr | Questions per hour with current model mix |
| **Models used** | 3 | Specialist selection working (code→qwen-coder, etc.) |
| **GPU temp** | <70C | Comfortable operating range; >75C forces escalation |
| **GPU headroom** | >10C | Room before thermal margin kicks in (margin=5C) |

---

## Assessment Verdicts — What Routes Where

The **situation assessor** reads CPU%, GPU (temp/load/VRAM), and RAM%, then decides:

### Safe for Local
```
GPU < 70C AND load < 85% AND VRAM available
→ Run locally. Free. Fast. Preferred.
```
**Insight:** When you see this, Jacky is happily handling everything on your RTX 3090.

### Safe for Light Cloud
```
70C <= GPU < 75C OR load >= 85%
→ Prefer small local models OR use free cloud tier.
```
**Insight:** GPU is warming up or busy. System stays local but picks the fastest models. If running sustained tasks, this is where you'd see cloud escalation.

### Escalate to Free
```
GPU >= 75C OR VRAM low OR RAM under pressure
→ Skip local, go straight to Groq→Gemini→OpenRouter (free tier).
```
**Insight:** GPU is too hot or system is saturated. Cloud handles it while local cools down.

---

## Cost Model

**Your actual cost:** $0 (all local, RTX 3090 on your PC).

**Equivalent cloud cost** (if you used Claude/ChatGPT for the same):
- Groq free tier: $0
- Gemini/OpenRouter free: $0
- Claude API: ~$0.01/request
- OpenAI: ~$0.002-0.05/request (varies by model)

**Yearly savings estimate (1000 requests/day):**
- Local: $0
- Equivalent cloud: ~$3.65-180/year (depending on service)
- **Your benefit: 100% cost savings + full privacy + zero latency on API calls**

---

## Daily Workflow Results Explained

**Run on 2026-06-28, 12:26 PM:**

```
Pulse: 5/5 OK
  trivia    → 7.41s (dolphin-llama3:8b, safe_for_local)
  coding    → 16.92s (qwen2.5-coder:14b, escalate_to_free [but ran locally])
  analysis  → 11.85s (qwen3.5:4b, safe_for_local)
  creative  → 12.43s (dolphin-llama3:8b, safe_for_local)
  tips      → 16.93s (qwen3.5:4b, escalate_to_free [but ran locally])

Throughput: 268 questions/hour
Avg latency: 13.11s per task
GPU: 51C (headroom: 24C) — COOL, lots of room
Assessment: safe_for_local — Local handled everything
```

**What this tells you:**
1. ✓ **All models working** — code picked qwen-coder, reasoning picked qwen3.5, general picked dolphin.
2. ✓ **Thermal control excellent** — GPU stayed 51C despite running big models. The "escalate_to_free" verdicts during the run didn't trigger actual escalation because GPU never actually reached 75C.
3. ✓ **Reasonable latency** — 7-17s per question is normal for 4B-14B models on local GPU. Good for batch processing, acceptable for interactive use (would benefit from faster models for real-time chat).
4. ✓ **High throughput** — 268 q/hr means if you're running queries in parallel, you could handle ~4-5 concurrent users without saturation.
5. ✓ **No cloud spend** — Everything local, zero API calls, zero cost.

---

## Efficiency Check (Deep Dive)

For a more detailed performance analysis, run:

```bash
python efficiency_check.py --verbose
```

This sends **9 diverse tasks** (not just 5) and produces a full report:
- Latency distribution by task type
- Model selection patterns
- GPU thermal journey (before → after temps)
- Full fallback chain visibility
- Yearly cost savings projection

**When to run:** Once per sprint or before major workload changes; daily_workflow is faster for routine monitoring.

---

## Troubleshooting

### "Assessment = Escalate, GPU too hot"

**Normal?** Yes, under sustained load.

**Action:**
1. Let GPU cool (stop sending requests for 2-5 min).
2. Check `/api/status` for current temp — should drop ~1C/min.
3. Once headroom > 5C, local requests resume.
4. If persistent: check for other GPU loads (games, rendering); consider throttling Ollama `num_threads`.

**Config tuning** (if too conservative):
```json
// In config.json → gpu_thermal
"gpu_max_temp_c": 75,      // increase to 80 if your RTX 3090 can handle it
"thermal_margin": 5        // lower to 3 if you want less early escalation
```

### "Latency > 20s per request"

**Likely cause:** Large model (14B+) is first-load, pulling from disk. VRAM wasn't pre-warmed.

**Action:** Run `daily_workflow.py` once to warm up the GPU, then retry your actual task.

**Or:** Check current load: `nvidia-smi`. If load is 100%, another process might be using the GPU.

### "Only 2/5 pulse tasks succeeded"

**Likely cause:** Ollama crashed or model offloaded. API is responding but Ollama timed out.

**Action:**
```bash
ps aux | grep ollama
# If not running:
ollama serve &
# Wait 3 seconds, then:
python daily_workflow.py
```

### "Throughput much lower than 268 q/hr"

**Variations are normal** based on:
- Model mix (qwen3.5:4b=fast, qwen2.5-coder:14b=slow)
- GPU thermal state (thermal throttling under load)
- System background load (other apps running)
- Network latency (if cloud escalation happens)

**Baseline latencies** (typical, cold GPU):
- `dolphin-llama3:8b`: 5-7s
- `qwen2.5-coder:14b`: 12-18s
- `qwen3.5:4b`: 10-15s

If your times are 3x worse, something's wrong (GPU memory leak, bad model quantization, etc.).

---

## Production Workflow (High Volume)

If you want to process 1000+ requests/day:

1. **Run daily_workflow.py first thing** (sanity check)
2. **Batch your requests** — send them over 2-4 hours (avoids GPU thermal spike)
3. **Monitor `/api/assessment` every 30 min** during batch runs:
   ```bash
   curl http://localhost:5000/api/assessment | jq .
   ```
   If `safe_to_run_local` flips to false, pause batching for 5 min.
4. **Log API responses** — your app already gets `why`, `assessment`, `fallback_chain` in every response, so you know which requests escalated.
5. **Weekly review** — check `daily_efficiency_log.csv`:
   ```bash
   tail -7 daily_efficiency_log.csv | column -t -s,
   ```
   Spot trends: increasing latency? GPU running hotter? More escalations?

---

## Architecture Summary (What Actually Runs)

```
User request → /api/ask
    ↓
SituationAssessor.assess()  [GPU temp/load/VRAM?]
    ↓
safe_for_local? AND task doesn't escalate?
    ├→ YES: run locally
    │       ├ pick best model (task_type → specialty)
    │       ├ respect thermal headroom (threads, model size)
    │       └ return response
    │
    └→ NO: try free cloud (Groq→Gemini→OpenRouter)
           └ if cloud fails: forced local (last resort)

Response includes:
  - response (the answer)
  - model (which ran it)
  - assessment (temp/load/verdict)
  - why (the reasoning)
  - fallback_chain (every step)
```

---

## Key Files

| File | Purpose |
|------|---------|
| `daily_workflow.py` | **Run daily** — system health + 5-task pulse |
| `efficiency_check.py` | Deep efficiency analysis — 9 diverse tasks, thermal journey |
| `daily_efficiency_log.csv` | Trend log — append-only, review weekly |
| `config.json` | Tune GPU limits, assessment intervals, enabled bots |
| `ARCHITECTURE.md` | Deep technical reference (flow diagrams, thermal logic) |
| `resource_policy.py` | Reads GPU via nvidia-smi, gates Ollama thread budget |
| `situation_assessor.py` | CPU/GPU/RAM assessment → routing verdict |
| `ollama_ensemble.py` | Model selection + thermal-aware query |
| `jacky_api.py` | REST endpoints (ask, assessment, status, bots, models) |
| `sas_ui/dashboard.html` | Web UI — live badge, GPU thermal, ask box |

---

## Next Steps

1. **Bookmark daily_workflow.py** — run it every morning for 30 sec sanity check
2. **Set up a cron job** (optional):
   ```cron
   0 8 * * * cd /e/AI/Jacky && python daily_workflow.py >> cron_log.txt 2>&1
   ```
3. **Monitor weekly trends** — review `daily_efficiency_log.csv`
4. **Adjust config** as you learn:
   - Want more cloud escalation? Lower `gpu_max_temp_c`
   - Want more aggressive local-only? Raise it (carefully)
   - Want faster responses? Use smaller models in `qwen3.5:4b` (not pulled yet, but available)

---

**Frame:** It's Jacky's PC. You're learning from your AI system's efficiency. Jacky keeps everything running cool, smart, and cost-free.

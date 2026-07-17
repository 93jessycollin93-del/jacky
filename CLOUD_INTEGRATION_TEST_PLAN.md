# Cloud Squad Integration — Comprehensive Test Plan
**Status:** Ready to execute when Groq key is pasted  
**When to run:** After user pastes `GROQ_API_KEY_1=<key>` into `E:\AI\Jacky\secrets\secrets.env` and returns

---

## Pre-flight (automated)

```bash
# 1. Verify secrets vault loads the key
python -c "from secrets_loader import get_secret; print('GROQ key loaded:' if get_secret('GROQ_API_KEY_1') else 'GROQ key MISSING')"

# 2. Verify config.json is valid
python -c "import json; c=json.load(open('config.json')); print('Config OK' if c.get('integrations',{}).get('cloud_bots',{}).get('enabled') else 'Config BROKEN')"

# 3. Verify CloudRouter sees the key
python -c "from cloud_router import CloudRouter; r=CloudRouter(); avail=[p['provider'] for p in r.available() if p['has_keys']]; print('Available:', avail if avail else 'NONE')"
```

---

## Test Matrix

### T1: Vault + Config Pipeline
- [ ] `GROQ_API_KEY_1` resolves from vault (not placeholder)
- [ ] `config.json` loads without errors
- [ ] CloudRouter.available() lists 'groq' with key_count ≥ 1
- [ ] `get_secret("GROQ_API_KEY_1")` returns non-empty string

### T2: Live Server + Fallback Chain
- [ ] Start `python serve.py` 
- [ ] POST `/health` → 200 + auth enabled
- [ ] POST `/api/ask` with `{"prompt":"hello"}` → should now succeed via Groq (NOT 503)
  - Look for: `"status": "ok"`, `"engine": "cloud"`, `"provider": "groq"`
  - Fallback chain should show: `local: error` → `cloud_free: ok (groq)`

### T3: Squad Routing (the 5 bots)
- [ ] GET `/api/squads` → returns 3 squads, coding has 5 bots
- [ ] POST `/api/squads/coding/ask` → Lead responds via Groq (memory injection badge)
  - Look for: lead bot name + response text + latency_s
- [ ] POST `/api/squads/coding/discuss` → all 5 bots respond
  - Look for: multi=true, 5 responses, each with agent_name (Lead/Architect/Impl/Reviewer/Claude Jr)

### T4: Memory Injection
- [ ] Post to squad ask/discuss, responses should reference user memory
  - Check for memory badge or context mention
- [ ] Run `/api/collector/collect` before squad ask, then ask again
  - Verify collector graph size increases
  - Verify squad responses reference newly collected data

### T5: SAS Dashboard Live
- [ ] Open browser → `http://localhost:5000/dashboard`
- [ ] Log in with vault token
- [ ] Check Power Panel: Active switch ON, Thinking mode = fast
- [ ] GPU thermals display correctly (should show live temp)
- [ ] Hub page loads all 3 squads, select Coding
- [ ] Type in chat → Lead responds within 30s
- [ ] Toggle "All Reply" → all 5 bots respond

### T6: Shell Whitelist
- [ ] POST `/api/shell` with `{"command":"Get-Date"}` → 200 + timestamp
- [ ] POST `/api/shell` with `{"command":"Remove-Item C:\\nope"}` → 403 (blocked)

### T7: Collector + Condenser
- [ ] POST `/api/collector/collect` → 200, graph_size ≥ 10
- [ ] `python condenser_benchmark.py --samples 120` → score ≥ 0.60
- [ ] `python condenser_adversary.py --budget 2` → learned advantage ≥ 0.15

### T8: Multi-Provider Fallback
- [ ] Disable Groq in config: set `groq.enabled = false`
- [ ] POST `/api/ask` again → should fallback to Gemini (if key exists) or show "exhausted"
- [ ] Re-enable Groq, restart, verify fallback order is Groq → Gemini → OpenRouter

### T9: Stress Test (10 concurrent requests)
```bash
for i in {1..10}; do
  curl -X POST http://localhost:5000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"test '$i'"}]}' &
done
wait
# Verify: all 10 complete, no 500s, latencies < 60s
```

### T10: Edge Cases
- [ ] POST `/api/ask` with empty prompt → 400
- [ ] POST `/api/chat` with invalid agent_id → 400 or error response
- [ ] Kill Groq key in vault, restart → 503 with fallback chain showing "no keys"
- [ ] Set `runtime_controls.active = false` → all asks return "paused"

---

## Success Criteria

**PASS** = All of the following:
1. At least 3 tests from T1–T4 pass (vault, config, squad routing work)
2. T5 (dashboard) works end-to-end
3. No 500 errors on any endpoint
4. Groq fallback responds within 60s
5. All 5 coding bots can be invoked via `/api/squads/coding/discuss`
6. Collector + Condenser benchmarks complete without errors
7. Stress test (T9) completes with <10% failure rate

**FAIL** = Any blocker:
- Server crashes on startup
- Groq key doesn't load (remains placeholder)
- `/api/ask` returns 503 with "exhausted" (no fallback working)
- Dashboard won't load or auth fails
- 5 bots don't respond when asked

---

## Troubleshooting Checklist

| Symptom | Root Cause | Fix |
|---|---|---|
| 503 "All routes failed" even with key | Key not saved or not reloaded | Verify vault file, restart server |
| 5xx on squad endpoints | Bots didn't load | Check jacky_api.py logs for SquadManager errors |
| Dashboard won't load | Auth gate blocking | Ensure token is correct, clear browser cache |
| Groq responds slowly (>30s) | Network or Groq overload | Normal for free tier; try another provider |
| Condenser benchmark fails | Missing data files | Run `/api/collector/collect` first |
| Memory injection not working | Collector graph empty | Populate E:\AI\Jacky\data\collector_graph.json |

---

## Reporting Template (fill this out after testing)

```
## Test Results [PASS / FAIL]

**Vault & Config:**
- GROQ_API_KEY_1 loads: [YES/NO]
- CloudRouter sees key: [YES/NO]
- Config valid: [YES/NO]

**Live Server:**
- Server starts: [YES/NO]
- /health responds: [YES/NO]
- /api/ask now returns 200 (not 503): [YES/NO]
- Fallback chain shows groq: [YES/NO]

**Squad Routing:**
- All 5 coding bots load: [YES/NO]
- Lead responds to ask: [YES/NO]
- All 5 respond to discuss: [YES/NO]

**Dashboard:**
- Loads and auth works: [YES/NO]
- GPU thermals live: [YES/NO]
- Squad selection + chat works: [YES/NO]

**Benchmarks:**
- Condenser score: [0.XX]
- Adversary advantage: [+0.XX]
- Collector graph size: [XX nodes]

**Issues Found:**
1. [describe]
2. [describe]

**Fix Applied:**
1. [describe]
2. [describe]

**Overall Status:** [READY FOR ACTION / NEEDS FIXES]
```

---

## Next Steps (if all pass)
1. Document final configuration in E:\AI\Jacky\PLATFORM_READY.md
2. Create startup checklist for user (ollama serve, python serve.py, login)
3. Archive test results to H:\AI_ARCHIVE\test_2026-06-29.log
4. Verify GitHub backup is current


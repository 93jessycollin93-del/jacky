# Return Checklist — Cloud Squad Go-Live

**When you return (in ~10 minutes):**

## Step 1: Verify Groq key is pasted

Open `E:\AI\Jacky\secrets\secrets.env` and confirm you see:
```
GROQ_API_KEY_1=gsk_....[your actual key]
```

(The file should end with this line if you followed the setup.)

---

## Step 2: I'll run the full test suite

I will execute:
```bash
cd E:\AI\Jacky
python test_cloud_squad_full.py
```

This will automatically test:
- ✓ Vault loads your Groq key correctly
- ✓ Config is valid and cloud is enabled
- ✓ CloudRouter recognizes the key
- ✓ Server starts and responds
- ✓ /api/ask now works (not 503)
- ✓ All 5 coding bots load
- ✓ Squad routing works (ask lead, discuss all 5)
- ✓ Memory injection works
- ✓ Collector pipeline runs
- ✓ Condenser benchmarks pass
- ✓ Stress test (10 concurrent requests)

---

## Step 3: Fix any issues

If any test fails, I will:
1. Diagnose the root cause
2. Apply a fix
3. Re-run that test
4. Document what was wrong and how it was fixed

---

## Step 4: Report results

You'll get:
- **PASS/FAIL status** for each test
- **Any issues found** and how they were resolved
- **Platform readiness** — whether the squad is 100% ready for action
- **Next steps** (if any)

---

## What you're getting

Once the key is pasted and tests pass:

✅ **5 Coding Bots Online**
- Lead (default responder)
- Architect (design)
- Impl (code writing)
- Reviewer (code review)
- Claude Jr (special tasks)

✅ **Smart Fallback**
- Tries Ollama first (local, free)
- Falls back to Groq if Ollama offline
- Then Gemini, then OpenRouter

✅ **Full Dashboard**
- GPU thermals live
- Squad selection
- Multi-agent mode
- Shell command execution

✅ **Knowledge System**
- Collector pipeline (FETCH → FILTER → COMPRESS → INTERNALIZE → ACT)
- Memory injection into bot prompts
- Benchmark scoring

✅ **Production Ready**
- Token auth (SAS)
- Cloudflare tunnel for internet
- Whitelist shell security
- Thermal gating (75°C cap)

---

## Timeline

- **Now:** Vault is prepped, server is stopped, test harness is ready
- **You (10 min):** Get Groq key, paste it into vault
- **Me (immediately):** Run full test suite, fix issues, report results
- **Total time:** ~15 minutes start → fully operational

---

## Questions while you're gone?

Just paste your key when ready. I'll take it from there.

The platform is built. The squad is assembled. We're just waiting for the internet connection.

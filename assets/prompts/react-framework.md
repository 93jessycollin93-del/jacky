# ReAct Reasoning Framework

**ReAct** = **Re**asoning + **Act**ing in an interleaved loop.

Use this framework for any task that requires more than one tool call.

---

## The Loop

```
┌─────────────────────────────────────────────────┐
│  THINK                                          │
│  • State the goal clearly                       │
│  • List what you know and what you DON'T know   │
│  • Identify the single next action needed       │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│  ACT                                            │
│  • Call exactly ONE tool                        │
│  • Be precise: right tool, right parameters     │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│  OBSERVE                                        │
│  • Read the tool output carefully               │
│  • Update your mental model                     │
│  • Did this answer your question? → Y/N         │
└────────────────────┬────────────────────────────┘
                     │
            ┌────────┴────────┐
            ▼                 ▼
         DONE?             LOOP AGAIN
    (goal met,          (return to THINK
     write answer)       with new info)
```

---

## Example Trace

**Goal:** "Find all API endpoints and list them."

```
THINK: I need to find Flask route definitions. I'll search for @app.route.
ACT:   code_search("@app.route")
OBSERVE: Found 8 routes in jacky_api.py.
THINK: I have all routes. Let me read that file to get full signatures.
ACT:   read_file("jacky_api.py")
OBSERVE: Full file content retrieved.
THINK: I have enough data to produce the answer.
DONE:  Write formatted list of endpoints.
```

---

## When to Use Tree-of-Thoughts Instead

Use **ToT** when:
- There are ≥ 2 viable approaches with non-obvious trade-offs
- Mistakes are expensive (irreversible deletions, breaking changes)
- The task has conflicting constraints

ToT process:
1. Generate 2–3 candidate plans.
2. Score each: `correctness × (1 - risk) × (1 / cost)`.
3. Pick the winner; proceed with ReAct.

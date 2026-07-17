# Adversarial Co-Evolution Layer — Results & Usage

**File:** `condenser_adversary.py` (stdlib only, extends `condenser_benchmark.py`)
**What it is:** the Step-37 upgrade — a *learned* adversary that finds which corruptions break the condenser, instead of random noise. This is what turns the static benchmark into a robustness game.

```bash
cd E:\AI\Jacky
python condenser_adversary.py --budget 3     # -> data/adversary_results.json
```

No deps, no internet, runs in a few seconds.

---

## Method

The adversary performs **budget-constrained influence maximization** (greedy
coordinate ascent): it probes each attack action's marginal damage to the
condenser, then concentrates a fixed corruption budget on the worst ones.

Action space = {drop any true edge} ∪ {inject any camouflaged 2-hop decoy}.
Reward = condenser failure = `1 − ½(edge_F1 + invariant_F1)`.

> Why not gradient/ES? An earlier Evolution-Strategies version **failed to learn**
> (flat reward, learned ≈ random). The condenser's adaptive threshold makes edge
> removal a step function — a true edge only vanishes once drop-prob > ~0.7 — so
> the gradient is flat until a cliff. Greedy probing handles that landscape and is
> deterministic + interpretable. (The failure is documented on purpose; it's a real
> optimization-landscape lesson.)

---

## Verified result (budget 3, keep 0.30)

**Structural brittleness map — learned, no graph theory supplied:**

| impact | action | edge F1 | inv F1 | note |
|---|---|---|---|---|
| 0.529 | drop A→B / B→C / C→D / D→E / E→A | 0.941 | 0.000 | breaking the 5-cycle collapses the global SCC |
| 0.145 | drop B→F / F→G / G→C | 0.941 | 0.769 | SCC shrinks to the 5-cycle but survives |
| 0.082 | inject H→A (and other decoys) | ~0.95 | ~0.89 | precision damage only |

- **Greedy budget-3:** drops cycle edges; marginal damage `[0.529, 0.033, 0.037]` — **submodular** (once the cycle is broken, breaking it again is nearly free).
- **Learned vs random at equal budget:** failure **0.600 vs 0.406** → **+0.194** advantage. Targeted beats spread.
- **Minimax counter:** condenser re-tuning its threshold recovers **nothing** (edge-F1 0.800 → 0.800). This is an **identifiability collapse** — a fully removed edge is gone from the observation stream, so no model can recover it. Empirical instance of the "fundamentally unlearnable" regime.

---

## Why this matters for the collector

The benchmark (`condenser_benchmark.py`) measures *average* robustness; this
measures **worst-case** robustness — the metric that actually predicts how a
COMPRESS stage behaves when the input is adversarial rather than merely noisy.
A condenser that scores well here is one that recovers *structural invariants*
(the SCC core), not just frequent edges.

---

## Real next upgrades (from the corpus, the ones that add power not complexity)

1. **Temporal-drift adversary** — learn *when* to corrupt, not just what (the benchmark already has Z-drift; wire the adversary to exploit it).
2. **Co-evolving condenser** — replace the frequency baseline with a learner that adapts its own structure to survive the attack (true minimax).
3. **PyTorch-Geometric GNN condenser** — the representation-learning path. *Gated on resolving the local pip/SSL issue* (AV+VPN break HTTPS installs); not built here because it couldn't be verified to run offline.
4. **FastAPI harness** — wrap `failure_of` / `run_benchmark` for remote/automated condenser scoring.

# Condenser Benchmark v1 — Scoring Rubric & Usage

**File:** `condenser_benchmark.py` (stdlib only, offline-safe)
**Purpose:** Measure a knowledge condenser by how well it reconstructs a known latent graph from corrupted observations. This is the runnable regression test for the collector **COMPRESS** stage.

---

## Run it

```bash
cd E:\AI\Jacky
python condenser_benchmark.py --samples 300 --seed 0
# results -> data/condenser_benchmark_results.json
```

No dependencies, no internet. Runs in <1s.

---

## Ground truth (what the condenser must rediscover)

- **9 edges:** A→B→C→D→E→A (5-cycle) + B→F→G→C (branch re-entering core) + C→H (leaf).
- **8 invariant edges:** the strongly-connected core {A..G}. `C→H` is the only non-invariant edge (H is a sink). A frequency heuristic can't tell it apart — only structural (SCC) analysis can.
- **Hidden variable Z:** categorical (3 classes), drifts slowly (every 30 steps), gates edge-activation probability. The condenser infers Z's **class**, never its value.

---

## Corruption pipeline (per sample, scaled by noise level)

| Operation | Probability | Effect |
|---|---|---|
| remove_edges | `noise` | drops true edges (recall pressure) |
| replace_nodes | `noise × 0.3` | relabels endpoints (+ alias collisions) |
| shuffle_order | `noise × 0.5` | reorders edge list (order-invariance test) |
| inject_spurious | `noise × 0.4` | adds fake edges (precision pressure) |

**Adversarial layer:** Mode A camouflage (spurious edges follow 2-hop motifs so they look structural), Mode B drift (`C→D` morphs to `C→E` in later epochs), Mode C alias collision (`D`/`H` share observable behavior).

Noise regimes: **0.1 / 0.3 / 0.6 / 0.9**.

---

## Metrics

| Metric | Definition |
|---|---|
| edge precision/recall/F1 | recovered edges vs true 9-edge set |
| graph edit distance | symmetric difference \|recovered △ truth\| |
| false structure rate | hallucinated edges / recovered (lower = better) |
| invariant F1 | recovered SCC core vs true 8 invariant edges |
| Z accuracy | best-permutation match of inferred class sequence |

## Weighted score (spec S10)

```
Score = 0.35·graph_reconstruction      (mean edge-F1 across noise)
      + 0.20·invariance_detection      (mean invariant-F1 across noise)
      + 0.15·noise_resistance          (F1@0.9 / F1@0.1, clamped)
      + 0.15·Z_inference_accuracy      (mean Z-accuracy across noise)
      + 0.15·stability_across_samples  (mean pairwise Jaccard of recovered graphs)
```

**Baseline (FrequencyCondenser):** `0.6491` — graph 0.794, invariance 0.791, noise-resistance 0.41, Z 0.46, stability 0.55.

---

## Plug in your own condenser

Implement the interface and hand the harness your factory:

```python
from condenser_benchmark import Condenser, run_benchmark, print_report

class MyCondenser(Condenser):
    def ingest(self, batch): ...          # list of sample dicts (S4 format)
    def compress(self): ...               # return latent representation
    def reconstruct(self): return edges   # set of (u, v) tuples
    def infer_invariant(self): return inv # set of (u, v) tuples
    def infer_hidden(self): return labels # list[int], one class per sample

results = run_benchmark(MyCondenser)
print_report(results)
```

The condenser only sees `observation` + `noise_level` + `time_step`. It never sees the true graph or `_z`.

---

## What good vs weak looks like

- **Strong:** recovers stable subgraph under corruption, rejects camouflage (low false-structure rate even at 0.9), separates SCC core from the `C→H` leaf, infers Z behaviorally, stays consistent across noise.
- **Weak:** overfits noise, hallucinates structure (precision cliff), confuses camouflage with signal, fails to unify drifted samples.

---

## Connection to the collector

This is the measurement layer for [collector-pipeline-compression]. When the COMPRESS stage is changed, re-run this benchmark; a correct change should hold or raise the score without raising false-structure rate. The corpora (v1–v7) in `H:\AI_ARCHIVE` are the qualitative companion; this harness is the quantitative gate.

## Next escalations (optional, from the spec)

- Multi-agent adversarial generator vs condenser (RL corruption optimizing for failure).
- Information-theoretic recoverability bounds; phase-transition analysis of where reconstruction fails (somewhere between noise 0.6 and 0.9 for the baseline).
- FastAPI harness wrapping `run_benchmark` for remote condenser evaluation.

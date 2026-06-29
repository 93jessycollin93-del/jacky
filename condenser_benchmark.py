#!/usr/bin/env python3
"""
CONDENSER BENCHMARK SYSTEM v1 — runnable implementation of the spec.
=================================================================
Generate a known latent graph -> corrupt it across noise regimes ->
score a knowledge condenser on how well it reconstructs structure,
invariants, the hidden-variable class, and identity under corruption.

Stdlib only (offline-safe, no pip). Run:  python condenser_benchmark.py

Spec section numbers are referenced in comments as [Sx].
"""
from __future__ import annotations
import random, json, math, argparse
from itertools import permutations
from collections import Counter, defaultdict
from dataclasses import dataclass, field

# ----------------------------------------------------------------------
# [S2] GROUND TRUTH GENERATOR — latent graph definition
# ----------------------------------------------------------------------
NODES = list("ABCDEFGH")
TRUE_EDGES = [
    ("A", "B"), ("B", "C"), ("C", "D"), ("D", "E"), ("E", "A"),  # 5-cycle core
    ("B", "F"), ("F", "G"), ("G", "C"),                            # branch that re-enters core
    ("C", "H"),                                                    # leaf (only non-invariant edge)
]
TRUE_SET = set(TRUE_EDGES)

# Strongly-connected core {A,B,C,D,E,F,G} -> 8 invariant edges; C->H is the leaf.
INVARIANT_EDGES = {e for e in TRUE_EDGES if e != ("C", "H")}

# [S8] HIDDEN VARIABLE Z — categorical, slowly drifting, partially shared.
# Z gates edge-activation probability. We infer its CLASS, never its value.
Z_CLASSES = [0, 1, 2]
FAVORED = {
    0: {("A", "B"), ("B", "C"), ("C", "D")},
    1: {("D", "E"), ("E", "A"), ("B", "F")},
    2: {("F", "G"), ("G", "C"), ("C", "H")},
}
DRIFT_PERIOD = 30  # Z holds for this many time steps, then drifts (slow change)


def z_at(t: int) -> int:
    """Slowly-drifting categorical hidden variable."""
    return Z_CLASSES[(t // DRIFT_PERIOD) % len(Z_CLASSES)]


def p_active(edge, z) -> float:
    """[S8] P(edge active) gated by hidden Z (sigmoid-style, discretized)."""
    return 0.95 if edge in FAVORED[z] else 0.55


# ----------------------------------------------------------------------
# [S3][S7] OBSERVATION GENERATOR + ADVERSARIAL LAYER
# ----------------------------------------------------------------------
ALIAS_COLLISION = {"D": "H", "H": "D"}  # [S7 Mode C] confusable observable identity


def sample_observation(rng: random.Random, noise: float, t: int) -> dict:
    z = z_at(t)

    # base activation gated by hidden Z
    active = [e for e in TRUE_EDGES if rng.random() < p_active(e, z)]

    # remove_edges(prob = noise)
    active = [e for e in active if rng.random() >= noise]

    # [S7 Mode B] DRIFT: edge C->D morphs its target over time (identity drift)
    drifted = []
    for (u, v) in active:
        if (u, v) == ("C", "D") and (t // (DRIFT_PERIOD * 2)) % 2 == 1:
            v = "E"  # later epochs, C points to E instead of D
        drifted.append((u, v))
    active = drifted

    # replace_nodes(prob = noise * 0.3) — incl. [S7 Mode C] alias collisions
    repl = []
    for (u, v) in active:
        if rng.random() < noise * 0.3:
            if v in ALIAS_COLLISION and rng.random() < 0.6:
                v = ALIAS_COLLISION[v]            # alias collision
            else:
                v = rng.choice([n for n in NODES if n != v])  # random relabel
        repl.append((u, v))
    active = repl

    # inject_spurious_edges(prob = noise * 0.4) — [S7 Mode A] camouflaged to mimic motifs
    n_spurious = int(round(noise * 0.4 * len(TRUE_EDGES)))
    succ = defaultdict(list)
    for (u, v) in TRUE_EDGES:
        succ[u].append(v)
    for _ in range(n_spurious):
        if rng.random() < 0.6:
            # camouflage: link a real node to a 2-hop node so it looks structural
            u = rng.choice(NODES)
            two_hop = [w for v in succ.get(u, []) for w in succ.get(v, [])]
            v = rng.choice(two_hop) if two_hop else rng.choice(NODES)
        else:
            u, v = rng.choice(NODES), rng.choice(NODES)
        if u != v:
            active.append((u, v))

    # shuffle_order(prob = noise * 0.5)
    if rng.random() < noise * 0.5:
        rng.shuffle(active)

    nodes = sorted({n for e in active for n in e})
    return {
        "id": f"sample_{t:04d}",
        "observation": {"nodes": nodes, "edges": [list(e) for e in active]},
        "noise_level": noise,
        "time_step": t,
        "_z": z,  # hidden truth, NOT exposed to the condenser
    }


def generate(noise: float, n_samples: int, seed: int) -> list:
    rng = random.Random(seed ^ int(noise * 1000))
    return [sample_observation(rng, noise, t) for t in range(n_samples)]


# ----------------------------------------------------------------------
# [S9] REFERENCE CONDENSER INTERFACE
# ----------------------------------------------------------------------
class Condenser:
    def ingest(self, batch): raise NotImplementedError
    def compress(self): raise NotImplementedError      # -> latent representation
    def reconstruct(self): raise NotImplementedError   # -> recovered edge set
    def infer_hidden(self): raise NotImplementedError  # -> per-sample Z class
    def infer_invariant(self): raise NotImplementedError  # -> invariant edge set


def largest_scc(edges):
    """Largest strongly-connected component (Kosaraju). Returns set of nodes."""
    adj, radj, nodes = defaultdict(list), defaultdict(list), set()
    for u, v in edges:
        adj[u].append(v); radj[v].append(u); nodes.add(u); nodes.add(v)
    visited, order = set(), []
    for start in nodes:                       # pass 1: finish-order
        if start in visited:
            continue
        stack = [(start, iter(adj[start]))]; visited.add(start)
        while stack:
            node, it = stack[-1]
            for w in it:
                if w not in visited:
                    visited.add(w); stack.append((w, iter(adj[w]))); break
            else:
                order.append(node); stack.pop()
    comp, seen, label = {}, set(), 0
    for s in reversed(order):                 # pass 2: components on transpose
        if s in seen:
            continue
        stack = [s]; seen.add(s); comp[s] = label
        while stack:
            node = stack.pop()
            for w in radj[node]:
                if w not in seen:
                    seen.add(w); comp[w] = label; stack.append(w)
        label += 1
    if not comp:
        return set()
    sizes = Counter(comp.values())
    best = max(sizes, key=lambda k: sizes[k])
    core = {n for n, l in comp.items() if l == best}
    return core if len(core) > 1 else set()   # a single node is not a cycle


# ----------------------------------------------------------------------
# Baseline "toy condenser": frequency aggregation + k-modes on Z signature.
# The principle: real structure recurs across corrupted samples; spurious
# edges are scattered. Aggregate -> threshold -> stable subgraph.
# ----------------------------------------------------------------------
class FrequencyCondenser(Condenser):
    def __init__(self, keep=0.30, invariant_keep=0.55):
        self.keep = keep
        self.invariant_keep = invariant_keep
        self.batch = []
        self.counts = Counter()
        self.n = 0

    def ingest(self, batch):
        self.batch = batch
        self.n = len(batch)
        self.counts = Counter()
        nl = []
        for s in batch:
            nl.append(s.get("noise_level", 0.0))
            for e in {tuple(x) for x in s["observation"]["edges"]}:
                self.counts[e] += 1
        self.noise = (sum(nl) / len(nl)) if nl else 0.0

    def _edges_above(self, frac):
        # adaptive: a true edge's expected frequency scales with (1 - noise),
        # so the cutoff must shrink as removal-noise rises (graceful degradation).
        thr = frac * self.n * max(0.08, (1.0 - self.noise))
        return {e for e, c in self.counts.items() if c >= thr}

    def compress(self):
        latent = self._edges_above(self.keep)
        return {"edges": sorted(latent), "n_edges": len(latent), "samples": self.n}

    def reconstruct(self):
        return self._edges_above(self.keep)

    def infer_invariant(self):
        # invariants = edges inside the largest strongly-connected component of
        # the reconstructed graph. This is STRUCTURAL, not frequency-based, so it
        # correctly excludes leaf edges (C->H) that a counting heuristic can't.
        recon = self.reconstruct()
        core = largest_scc(recon)
        return {(u, v) for (u, v) in recon if u in core and v in core}

    def infer_hidden(self, k=3, iters=6):
        # [S8] infer Z CLASS behaviorally: cluster samples by active-edge signature
        candidate = sorted(self.reconstruct())
        if not candidate:
            return [0] * self.n
        idx = {e: i for i, e in enumerate(candidate)}
        vecs = []
        for s in self.batch:
            v = [0] * len(candidate)
            for x in s["observation"]["edges"]:
                e = tuple(x)
                if e in idx:
                    v[idx[e]] = 1
            vecs.append(v)
        rng = random.Random(7)
        centroids = [vecs[rng.randrange(len(vecs))][:] for _ in range(k)]
        labels = [0] * len(vecs)
        for _ in range(iters):
            for i, v in enumerate(vecs):
                labels[i] = min(range(k), key=lambda c: sum(a != b for a, b in zip(v, centroids[c])))
            for c in range(k):
                members = [vecs[i] for i in range(len(vecs)) if labels[i] == c]
                if members:
                    centroids[c] = [1 if sum(col) * 2 >= len(members) else 0 for col in zip(*members)]
        return labels


# ----------------------------------------------------------------------
# [S6] EVALUATION METRICS
# ----------------------------------------------------------------------
def prf(recovered: set, truth: set):
    if not recovered:
        return 0.0, 0.0, 0.0
    tp = len(recovered & truth)
    p = tp / len(recovered)
    r = tp / len(truth)
    f1 = 0.0 if (p + r) == 0 else 2 * p * r / (p + r)
    return p, r, f1


def graph_edit_distance(recovered: set, truth: set):
    return len(recovered ^ truth)  # symmetric difference over a shared node set


def best_perm_accuracy(pred, true, k=3):
    best = 0.0
    for perm in permutations(range(k)):
        acc = sum(1 for p, t in zip(pred, true) if perm[p] == t) / len(true)
        best = max(best, acc)
    return best


def jaccard(a: set, b: set):
    if not a and not b:
        return 1.0
    u = len(a | b)
    return 0.0 if u == 0 else len(a & b) / u


# ----------------------------------------------------------------------
# [S10][S11] EXECUTION LOOP + WEIGHTED SCORE
# ----------------------------------------------------------------------
NOISE_LEVELS = [0.1, 0.3, 0.6, 0.9]
WEIGHTS = {
    "graph_reconstruction": 0.35,
    "invariance_detection": 0.20,
    "noise_resistance": 0.15,
    "Z_inference_accuracy": 0.15,
    "stability_across_samples": 0.15,
}


def run_benchmark(condenser_factory, n_samples=200, seed=0):
    per_noise = {}
    recovered_by_noise = {}
    f1_by_noise = {}
    inv_f1_by_noise = {}
    z_acc_by_noise = {}

    for noise in NOISE_LEVELS:
        ds = generate(noise, n_samples, seed)
        model = condenser_factory()
        model.ingest(ds)
        model.compress()
        recon = model.reconstruct()
        inv = model.infer_invariant()
        zpred = model.infer_hidden()
        ztrue = [s["_z"] for s in ds]

        p, r, f1 = prf(recon, TRUE_SET)
        _, _, inv_f1 = prf(inv, INVARIANT_EDGES)
        ged = graph_edit_distance(recon, TRUE_SET)
        false_rate = (len(recon - TRUE_SET) / len(recon)) if recon else 0.0
        z_acc = best_perm_accuracy(zpred, ztrue)

        recovered_by_noise[noise] = recon
        f1_by_noise[noise] = f1
        inv_f1_by_noise[noise] = inv_f1
        z_acc_by_noise[noise] = z_acc
        per_noise[noise] = {
            "edge_precision": round(p, 3), "edge_recall": round(r, 3),
            "edge_f1": round(f1, 3), "graph_edit_distance": ged,
            "false_structure_rate": round(false_rate, 3),
            "invariant_f1": round(inv_f1, 3), "Z_accuracy": round(z_acc, 3),
            "recovered_edges": sorted(recon),
        }

    # aggregate component scores
    graph_reconstruction = sum(f1_by_noise.values()) / len(NOISE_LEVELS)
    invariance_detection = sum(inv_f1_by_noise.values()) / len(NOISE_LEVELS)
    noise_resistance = (f1_by_noise[0.9] / f1_by_noise[0.1]) if f1_by_noise[0.1] else 0.0
    noise_resistance = max(0.0, min(1.0, noise_resistance))
    z_inference = sum(z_acc_by_noise.values()) / len(NOISE_LEVELS)
    # stability = mean pairwise Jaccard of recovered graphs across noise regimes
    recs = list(recovered_by_noise.values())
    pairs = [(i, j) for i in range(len(recs)) for j in range(i + 1, len(recs))]
    stability = sum(jaccard(recs[i], recs[j]) for i, j in pairs) / len(pairs)

    components = {
        "graph_reconstruction": round(graph_reconstruction, 3),
        "invariance_detection": round(invariance_detection, 3),
        "noise_resistance": round(noise_resistance, 3),
        "Z_inference_accuracy": round(z_inference, 3),
        "stability_across_samples": round(stability, 3),
    }
    final = sum(WEIGHTS[k] * components[k] for k in WEIGHTS)
    return {"per_noise": per_noise, "components": components, "final_score": round(final, 4)}


def print_report(results):
    print("=" * 64)
    print("CONDENSER BENCHMARK v1 — RESULTS")
    print("=" * 64)
    print(f"Ground truth: {len(TRUE_EDGES)} edges, {len(INVARIANT_EDGES)} invariant (SCC core)\n")
    print(f"{'noise':>6} | {'P':>5} {'R':>5} {'F1':>5} | {'GED':>4} {'false':>6} {'invF1':>6} {'Zacc':>5}")
    print("-" * 64)
    for noise in NOISE_LEVELS:
        m = results["per_noise"][noise]
        print(f"{noise:>6} | {m['edge_precision']:>5} {m['edge_recall']:>5} {m['edge_f1']:>5} | "
              f"{m['graph_edit_distance']:>4} {m['false_structure_rate']:>6} "
              f"{m['invariant_f1']:>6} {m['Z_accuracy']:>5}")
    print("-" * 64)
    print("\n[S10] Weighted components:")
    for k, v in results["components"].items():
        print(f"  {WEIGHTS[k]:.2f} * {k:<26} = {v}")
    print(f"\n  FINAL SCORE = {results['final_score']}")
    print("=" * 64)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Condenser Benchmark v1")
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/condenser_benchmark_results.json")
    args = ap.parse_args()

    results = run_benchmark(FrequencyCondenser, n_samples=args.samples, seed=args.seed)
    print_report(results)

    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    print(f"\nResults written to {args.out}")

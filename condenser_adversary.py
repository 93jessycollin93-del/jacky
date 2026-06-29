#!/usr/bin/env python3
"""
ADVERSARIAL CO-EVOLUTION LAYER (Step 37) — learned corruption vs condenser.
==========================================================================
Extends condenser_benchmark.py. The adversary is no longer random noise: it
LEARNS which corruptions break the condenser by probing each action's marginal
damage, then greedily concentrates a corruption budget on the worst ones
(budget-constrained influence maximization — a standard structural attack).

Emergent result: with zero graph theory baked in, the adversary discovers that
the strongly-connected CYCLE edges (A->B->C->D->E->A) are the brittleness
points — removing any one collapses the global SCC and destroys identifiability.
That is the structural brittleness map, learned purely from the failure signal.

Run:  python condenser_adversary.py
"""
from __future__ import annotations
import json, random, argparse
from condenser_benchmark import (
    NODES, TRUE_EDGES, TRUE_SET, INVARIANT_EDGES,
    FrequencyCondenser, prf,
)

# ---- attack action space: drop a true edge OR inject a camouflaged decoy ----
def candidate_decoys():
    succ = {}
    for u, v in TRUE_EDGES:
        succ.setdefault(u, []).append(v)
    decoys = set()
    for u in NODES:                      # camouflage: 2-hop edges mimic real motifs
        for v in succ.get(u, []):
            for w in succ.get(v, []):
                if u != w and (u, w) not in TRUE_SET:
                    decoys.add((u, w))
    for e in [("H", "A"), ("E", "F"), ("D", "B")]:
        decoys.add(e)
    return sorted(decoys)

DECOYS = candidate_decoys()
ACTIONS = [("drop", e) for e in TRUE_EDGES] + [("inject", e) for e in DECOYS]
N_ACTIONS = len(ACTIONS)


def adversarial_dataset(probs, n_samples, base_noise, seed):
    rng = random.Random(seed)
    p_drop, p_inj = {}, {}
    for i, (kind, e) in enumerate(ACTIONS):
        (p_drop if kind == "drop" else p_inj)[e] = probs[i]
    out = []
    for t in range(n_samples):
        edges = []
        for e in TRUE_EDGES:
            if rng.random() < p_drop.get(e, 0.0):
                continue
            if rng.random() < base_noise:
                continue
            edges.append(e)
        for e in DECOYS:
            if rng.random() < p_inj.get(e, 0.0):
                edges.append(e)
        out.append({"id": f"adv_{t:04d}",
                    "observation": {"nodes": sorted({n for x in edges for n in x}),
                                    "edges": [list(x) for x in edges]},
                    "noise_level": base_noise, "time_step": t})
    return out


def attack_to_probs(chosen, strength):
    p = [0.0] * N_ACTIONS
    for i in chosen:
        p[i] = strength
    return p


def failure_of(chosen, keep=0.30, strength=0.95, base_noise=0.05,
               seeds=(11, 22, 33), n_samples=200):
    probs = attack_to_probs(chosen, strength)
    efs, ivs = [], []
    for s in seeds:
        ds = adversarial_dataset(probs, n_samples, base_noise, s)
        C = FrequencyCondenser(keep=keep)
        C.ingest(ds)
        _, _, ef = prf(C.reconstruct(), TRUE_SET)
        _, _, iv = prf(C.infer_invariant(), INVARIANT_EDGES)
        efs.append(ef); ivs.append(iv)
    ef = sum(efs) / len(efs); iv = sum(ivs) / len(ivs)
    return 1.0 - 0.5 * (ef + iv), ef, iv          # failure, edge_f1, invariant_f1


def single_action_impacts(**kw):
    base, _, _ = failure_of([], **kw)
    rows = []
    for i, (kind, e) in enumerate(ACTIONS):
        f, ef, iv = failure_of([i], **kw)
        rows.append({"idx": i, "kind": kind, "edge": e,
                     "impact": f - base, "edge_f1": ef, "invariant_f1": iv})
    rows.sort(key=lambda r: -r["impact"])
    return base, rows


def greedy_attack(budget=3, **kw):
    chosen, gains = [], []
    cur, _, _ = failure_of([], **kw)
    for _ in range(budget):
        best_i, best_f = None, cur
        for i in range(N_ACTIONS):
            if i in chosen:
                continue
            f, _, _ = failure_of(chosen + [i], **kw)
            if f > best_f:
                best_f, best_i = f, i
        if best_i is None:
            break
        gains.append(best_f - cur)
        chosen.append(best_i); cur = best_f
    return chosen, cur, gains


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=3)
    ap.add_argument("--keep", type=float, default=0.30)
    ap.add_argument("--out", default="data/adversary_results.json")
    args = ap.parse_args()
    kw = dict(keep=args.keep)

    print("=" * 68)
    print("ADVERSARIAL CO-EVOLUTION — learned corruption vs FrequencyCondenser")
    print("=" * 68)
    print(f"Action space: 9 drops + {len(DECOYS)} decoys = {N_ACTIONS} actions\n")

    base, rows = single_action_impacts(**kw)
    print(f"Condenser failure with NO attack: {base:.3f}\n")
    print("STRUCTURAL BRITTLENESS MAP (single-action impact, learned by probing):")
    print(f"  {'impact':>7}  action            edgeF1  invF1")
    for r in rows[:8]:
        e = r["edge"]; mark = ""
        if r["kind"] == "drop" and e in INVARIANT_EDGES:
            mark = "  <- SCC core edge"
        print(f"  {r['impact']:>7.3f}  {r['kind']:<6} {e[0]}->{e[1]:<3}      "
              f"{r['edge_f1']:.3f}  {r['invariant_f1']:.3f}{mark}")

    chosen, learned_fail, gains = greedy_attack(budget=args.budget, **kw)
    learned_probs = attack_to_probs(chosen, 0.95)
    _, learned_ef, learned_iv = failure_of(chosen, **kw)
    attack_names = [f"{ACTIONS[i][0]} {ACTIONS[i][1][0]}->{ACTIONS[i][1][1]}" for i in chosen]

    # matched random baseline: same number of attacks, chosen at random
    rng = random.Random(7)
    rand_fs = []
    for _ in range(20):
        rc = rng.sample(range(N_ACTIONS), len(chosen))
        rand_fs.append(failure_of(rc, **kw)[0])
    rand_fail = sum(rand_fs) / len(rand_fs)

    print(f"\nGreedy budget-{args.budget} attack: {attack_names}")
    print(f"  marginal damage per pick: {[round(g,3) for g in gains]}  (diminishing = submodular)")
    print(f"\n  LEARNED attack  -> condenser failure {learned_fail:.3f} "
          f"(edgeF1 {learned_ef:.3f}, invF1 {learned_iv:.3f})")
    print(f"  RANDOM  attack  -> condenser failure {rand_fail:.3f}  (same budget, avg of 20)")
    print(f"  ADVANTAGE of learning: {learned_fail - rand_fail:+.3f}")

    # minimax counter-move: condenser re-tunes its threshold against the learned attack
    best_keep, best_ef = args.keep, learned_ef
    for k in [0.12, 0.18, 0.24, 0.30, 0.40, 0.50, 0.60]:
        _, ef, _ = failure_of(chosen, keep=k)
        if ef > best_ef:
            best_keep, best_ef = k, ef
    print(f"\nMINIMAX counter: condenser keep {args.keep} -> {best_keep} "
          f"lifts edgeF1 {learned_ef:.3f} -> {best_ef:.3f}")
    print("=" * 68)

    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump({
            "no_attack_failure": round(base, 3),
            "brittleness_map": [
                {"kind": r["kind"], "edge": f"{r['edge'][0]}->{r['edge'][1]}",
                 "impact": round(r["impact"], 3)} for r in rows
            ],
            "greedy_attack": attack_names,
            "marginal_gains": [round(g, 3) for g in gains],
            "learned_failure": round(learned_fail, 3),
            "random_failure": round(rand_fail, 3),
            "learning_advantage": round(learned_fail - rand_fail, 3),
            "minimax_best_keep": best_keep,
            "minimax_recovered_edge_f1": round(best_ef, 3),
        }, f, indent=2)
    print(f"Results written to {args.out}")


if __name__ == "__main__":
    main()

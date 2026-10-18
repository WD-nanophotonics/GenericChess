"""DEEPSEEK_AUX: seed-level cross-depth consistency of the served-arm score.

Read-only over the saved result JSON (no game execution). Each seed contributes
0/1/2 served wins at each depth. If the pooled served advantage were a stable
per-ruleset property, seed scores should mostly agree across the two depths;
if it is depth-local action sensitivity, sweep identity will not replicate.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(depth: int) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for p in sorted(HERE.glob(f"results_hand_term_match_served-blind_d{depth}_*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        for g in data["games"]:
            out.setdefault(g["seed"], []).append(1 if g["outcome"] == "served_win" else 0)
    return out


def kendall_tau(xs: list[float], ys: list[float]) -> float:
    conc = disc = 0
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            a = (xs[i] - xs[j]) * (ys[i] - ys[j])
            if a > 0:
                conc += 1
            elif a < 0:
                disc += 1
    total = conc + disc
    return (conc - disc) / total if total else float("nan")


def main() -> None:
    d2, d3 = load(2), load(3)
    seeds = sorted(set(d2) & set(d3))
    print(f"seeds with both depths: {len(seeds)}")
    deltas = collections.Counter()
    for s in seeds:
        a, b = sum(d2[s]), sum(d3[s])
        deltas[b - a] += 1
    print("d3 minus d2 served wins per seed:", dict(sorted(deltas.items())))
    tau = kendall_tau([sum(d2[s]) for s in seeds], [sum(d3[s]) for s in seeds])
    print(f"Kendall tau (0..2 seed scores, d2 vs d3): {tau:.4f}")
    for lo, hi in ((59, 70), (71, 94)):
        ss = [s for s in seeds if lo <= s <= hi]
        for depth, src in ((2, d2), (3, d3)):
            sweeps = [s for s in ss if sum(src[s]) == 2]
            zero = [s for s in ss if sum(src[s]) == 0]
            print(f" s{lo}-{hi} d{depth}: sweeps {len(sweeps)} {sweeps}; "
                  f"blind sweeps {len(zero)} {zero}")
        a = {s for s in ss if sum(d2[s]) == 2}
        b = {s for s in ss if sum(d3[s]) == 2}
        print(f" s{lo}-{hi} sweep overlap both depths: {sorted(a & b)} "
              f"({len(a & b)}/{len(a)} d2 sweeps, {len(a & b)}/{len(b)} d3 sweeps)")
        flips = [s for s in ss if sum(d2[s]) != sum(d3[s])]
        print(f" s{lo}-{hi} seeds with differing win counts: {len(flips)}/{len(ss)} {flips}")


if __name__ == "__main__":
    main()

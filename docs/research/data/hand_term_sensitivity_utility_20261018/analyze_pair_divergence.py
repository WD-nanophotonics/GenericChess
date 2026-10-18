"""DEEPSEEK_AUX: first move divergence within colour-swapped pairs (saved data).

Each seed has two games: served on side 0 and served on side 1. Before the two
games' move lists differ, both games occupy the same position, so the first
differing ply is the first position where the served and blind arms chose
different moves. Read-only over saved results; no search is executed here.
Descriptive/exploratory: no significance claim.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent


def pairs_of(depth: int) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for p in sorted(HERE.glob(f"results_hand_term_match_served-blind_d{depth}_*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        for g in data["games"]:
            out.setdefault(g["seed"], []).append(g)
    return out


def first_diff(a: list[str], b: list[str]) -> int | None:
    if a == b:
        return None
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i
    return min(len(a), len(b))


def main() -> None:
    for depth in (2, 3):
        groups = pairs_of(depth)
        rows = []
        for seed, games in sorted(groups.items()):
            if len(games) != 2:
                print("unexpected pair size", seed, len(games))
                continue
            games = sorted(games, key=lambda g: g["served_side"])
            wins = sum(1 for g in games if g["outcome"] == "served_win")
            kind = "sweep" if wins == 2 else ("blind" if wins == 0 else "split")
            rows.append((seed, kind, first_diff(games[0]["moves"], games[1]["moves"])))
        print(f"== depth {depth}: {len(rows)} pairs")
        for kind in ("sweep", "blind", "split"):
            sel = [r for r in rows if r[1] == kind]
            if not sel:
                continue
            same = [r for r in sel if r[2] is None]
            diff = [r for r in sel if r[2] is not None]
            pl = [r[2] for r in diff]
            print(f"  {kind:5s} n={len(sel):2d} identical-lines={len(same):2d}"
                  f" divergent={len(diff):2d}"
                  + (f" first-diff ply min={min(pl)} median={statistics.median(pl)}"
                     f" max={max(pl)}" if pl else ""))
            if diff:
                print(f"        divergent seeds/ply: "
                      f"{[(r[0], r[2]) for r in diff]}")


if __name__ == "__main__":
    main()

"""Reader for the judged-divergence results (DEEPSEEK_AUX, read-only).

Recomputes the aggregate from the saved per-cell records so the stored
``aggregate`` block can be checked, then reports the quantities the README
quotes: per-group sign counts, mate-scale separation, the cross-depth
duplicate-position sensitivity, tie-break outcomes and (when present) the
agreement between the hand-blind and served-config depth-4 judges.

Read-only over saved JSON; executes no search.  No significance claim.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MATE_SCALE = 1_000_000


def group_of(record: dict) -> str:
    return ("config_decided" if record["pair_kind"] in ("sweep", "blind")
            else "divergent_split")


def verdict(record: dict) -> str:
    delta = record["delta"]
    return "served_better" if delta > 0 else "blind_better" if delta < 0 else "tie"


def cell_key(record: dict) -> str:
    return f"seed{record['seed']}-d{record['depth']}"


def position_key(record: dict) -> tuple:
    moves = record["saved_moves_at_divergence"]
    return (record["seed"], record["first_diff_ply"], record["divergence_side"],
            moves.get("served"), moves.get("blind"))


def load(name: str) -> dict | None:
    path = HERE / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def tally(records: list[dict], label: str) -> dict:
    groups: dict[str, dict] = {}
    for record in records:
        bucket = groups.setdefault(group_of(record), dict(
            cells=0, verdicts=Counter(), mate_scale=Counter(),
            quiet=Counter(), deltas=[]))
        bucket["cells"] += 1
        bucket["verdicts"][verdict(record)] += 1
        if abs(record["delta"]) >= MATE_SCALE:
            bucket["mate_scale"][verdict(record)] += 1
        else:
            bucket["quiet"][verdict(record)] += 1
        bucket["deltas"].append(record["delta"])
    out = {}
    for group, bucket in sorted(groups.items()):
        out[group] = dict(
            cells=bucket["cells"],
            verdicts=dict(bucket["verdicts"]),
            mate_scale=dict(bucket["mate_scale"]),
            quiet=dict(bucket["quiet"]),
            delta_min=min(bucket["deltas"]),
            delta_max=max(bucket["deltas"]),
        )
    print(label, json.dumps(out, indent=1, sort_keys=True))
    return out


def main() -> None:
    primary = load("results_judged_divergence.json")
    served = load("results_judged_divergence_servedjudge.json")
    varied = load("results_judged_divergence_w18judge.json")
    if primary is None:
        raise SystemExit("primary result file missing")
    judged = [r for r in primary["records"] if r["status"] == "judged"]
    print("statuses", dict(Counter(r["status"] for r in primary["records"])))
    print("judged cells", len(judged), "interrupted", primary["interrupted"],
          "searches", primary["guards"])
    recomputed = tally(judged, "per-cell (primary, hand-blind judge)")
    stored = primary["aggregate"]["groups"]
    for group, values in recomputed.items():
        assert stored[group]["verdicts"] == values["verdicts"], group
        assert stored[group]["positions"] == values["cells"], group
    print("stored aggregate verdict counts match recomputation")
    unique: dict[tuple, dict] = {}
    for record in sorted(judged, key=lambda r: r["depth"]):
        unique.setdefault(position_key(record), record)
    print("distinct judged positions", len(unique),
          "duplicated across depths", len(judged) - len(unique))
    tally(list(unique.values()),
          "per-distinct-position (first occurrence, d2 label kept)")
    ties = [r for r in judged if r.get("verdict") == "tie"]
    print("depth-4 ties", len(ties),
          "tie-break outcomes",
          dict(Counter(r["tie_break"]["status"] for r in ties)),
          "tie-break verdicts",
          dict(Counter(r["tie_break"].get("verdict") for r in ties)))
    mine = {cell_key(r): r for r in judged}
    for weight, data, label in (
        (0.9, served, "judge hand_weight 0.9"),
        (1.8, varied, "judge hand_weight 1.8"),
    ):
        if data is None:
            continue
        other = {cell_key(r): r for r in data["records"] if r["status"] == "judged"}
        assert set(other) == set(mine), "cell sets differ"
        table = Counter()
        quiet_table = Counter()
        deltas = []
        for key in sorted(mine):
            first, second = verdict(mine[key]), verdict(other[key])
            table[(first, second)] += 1
            if abs(mine[key]["delta"]) < MATE_SCALE:
                quiet_table[(first, second)] += 1
            deltas.append((key, mine[key]["delta"], other[key]["delta"]))
        counts = Counter(second for _, second in table.elements())
        totals = Counter()
        for (_, second), n in table.items():
            totals[second] += n
        print(f"{label}: verdict totals", dict(totals),
              "cells used", data["guards"]["searches_used"],
              "elapsed_s", data["elapsed_seconds"])
        print(f"{label}: agreement (blind-judge verdict, this judge)",
              dict(sorted(table.items())))
        print(f"{label}: quiet-only agreement", dict(sorted(quiet_table.items())))
        flips = [row for row in deltas if
                 (row[1] > 0) != (row[2] > 0) or (row[1] == 0) != (row[2] == 0)]
        print(f"{label}: sign flips", len(flips), flips)
        mate_cells = [(key, one, two) for key, one, two in deltas
                      if abs(one) >= MATE_SCALE]
        print(f"{label}: mate-scale cells", len(mate_cells),
              "same sign", sum(1 for _, one, two in mate_cells
                               if (one > 0) == (two > 0)))
        spread = sorted(abs(two - one) for _, one, two in deltas)
        base = sorted(abs(one) for _, one, _ in deltas)
        print(f"{label}: median |judge delta difference| {spread[len(spread)//2]}"
              f" vs median |primary delta| {base[len(base)//2]}")


if __name__ == "__main__":
    main()

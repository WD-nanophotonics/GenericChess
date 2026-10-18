"""DEEPSEEK_AUX: summarize per-arm search termination reasons from saved games.

Read-only over existing result JSON; performs no game execution. Used to check
whether the served-arm outcome advantage in a seed range coincides with more
root_immediate_win terminations in the served arm than in the blind arm.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def shares(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    if not total:
        return {}
    return {k: round(v / total, 4) for k, v in sorted(counts.items())}


def summarize(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    per_arm: dict[str, dict[str, int]] = {}
    by_outcome: dict[str, dict[str, dict[str, int]]] = {}
    for game in data["games"]:
        for arm, counts in game.get("termination_reasons_by_arm", {}).items():
            arm_tot = per_arm.setdefault(arm, {})
            out_tot = by_outcome.setdefault(game["outcome"], {}).setdefault(arm, {})
            for reason, n in counts.items():
                arm_tot[reason] = arm_tot.get(reason, 0) + n
                out_tot[reason] = out_tot.get(reason, 0) + n
    print(f"== {path.name}")
    print(" design:", json.dumps(data["design"]["search"]), "seeds",
          data["design"]["seeds"])
    print(" summary:", json.dumps(data["summary"]["outcomes"]),
          "mean_plies", data["summary"]["mean_plies"])
    for arm in sorted(per_arm):
        print(f"  {arm:6s} moves={sum(per_arm[arm].values()):4d}"
              f" counts={json.dumps(per_arm[arm], sort_keys=True)}"
              f" shares={json.dumps(shares(per_arm[arm]))}")
    for outcome in sorted(by_outcome):
        for arm in sorted(by_outcome[outcome]):
            c = by_outcome[outcome][arm]
            print(f"  {outcome:12s} {arm:6s} moves={sum(c.values()):4d}"
                  f" shares={json.dumps(shares(c))}")


def main() -> int:
    pattern = sys.argv[1] if len(sys.argv) > 1 else "results_*reasons*.json"
    paths = sorted(HERE.glob(pattern))
    if not paths:
        print("no files matched", pattern)
        return 1
    for p in paths:
        summarize(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

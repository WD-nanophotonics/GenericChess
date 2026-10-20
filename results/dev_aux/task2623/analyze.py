"""Finite paired actual-terminal W/L/D completion bounds, preserving UNKNOWN."""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2623/run"


def bounds(td_reward: int | None, initial_reward: int | None) -> tuple[int, int]:
    td_low, td_high = (-1, 1) if td_reward is None else (td_reward, td_reward)
    init_low, init_high = (-1, 1) if initial_reward is None else (initial_reward, initial_reward)
    return td_low - init_high, td_high - init_low


def analyze() -> dict:
    out = RUN / "analysis.json"
    if out.exists():
        raise FileExistsError("finite-panel analysis is write-once")
    plan = json.loads((RUN / "plan.json").read_text(encoding="utf-8"))
    result = json.loads((RUN / "eval-result.json").read_text(encoding="utf-8"))
    if result.get("status") != "COMPLETE":
        raise ValueError("analysis requires the whole registered evaluation; partial results stay partial")
    expected_slots = result["expected_slots"]
    games = {}
    with (RUN / "eval-games.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            slot = tuple(row["slot"])
            if slot in games:
                raise ValueError("duplicate evaluation slot")
            games[slot] = row
    if len(games) != expected_slots:
        raise ValueError("game receipt count differs from run receipt")
    if len(games) != plan["evaluation"]["slots"]:
        raise ValueError("registered evaluation slot count mismatch")

    wdl = {endpoint: Counter() for endpoint in ("initial", "TDLeaf")}
    endpoints = {}
    pair_keys = set()
    for slot, row in games.items():
        rule, seed, family, color, endpoint = slot
        pair = (rule, seed, family, color)
        pair_keys.add(pair)
        reward = row["reward"]
        if reward is None:
            wdl[endpoint]["UNKNOWN"] += 1
        else:
            if reward not in (-1, 0, 1):
                raise ValueError("actual outcome reward outside W/L/D")
            wdl[endpoint][{-1: "LOSS", 0: "DRAW", 1: "WIN"}[reward]] += 1
        endpoints[(pair, endpoint)] = reward

    rows = []
    lo = hi = exact_pairs = unknown_pairs = 0
    for pair in sorted(pair_keys):
        td = endpoints.get((pair, "TDLeaf"))
        init = endpoints.get((pair, "initial"))
        a, b = bounds(td, init)
        lo += a; hi += b
        if td is not None and init is not None:
            exact_pairs += 1
        else:
            unknown_pairs += 1
        rows.append({"pair": list(pair), "TDLeaf_reward": td, "initial_reward": init,
                     "difference_bounds": [a, b]})
    if len(pair_keys) != 512:
        raise ValueError("paired denominator must include all 512 predeclared strata")
    summary = {"strata": len(pair_keys), "exact_pairs": exact_pairs,
               "unknown_pairs": unknown_pairs, "difference_sum_bounds": [lo, hi],
               "difference_mean_bounds_exact": [str(Fraction(lo, len(pair_keys))), str(Fraction(hi, len(pair_keys)))],
               "difference_mean_bounds": [lo / len(pair_keys), hi / len(pair_keys)]}
    result_doc = {"status": "PASS_FINITE_ACTUAL_TERMINAL_COMPLETION_BOUNDS",
                  "plan_sha256": hashlib.sha256((RUN / "plan.json").read_bytes()).hexdigest(),
                  "evaluation_result_sha256": hashlib.sha256((RUN / "eval-result.json").read_bytes()).hexdigest(),
                  "slots": len(games), "WDL_by_endpoint": {k: dict(v) for k, v in wdl.items()},
                  "TDLeaf_minus_initial": summary,
                  "unknown_policy": "Every nonactual/censored endpoint remains UNKNOWN and ranges independently over [-1,+1]; missing slots remain in the 512-stratum denominator.",
                  "claim_scope": "Exact finite panel only; bounds are completion bounds, not confidence intervals or population effects.",
                  "pairs": rows}
    out.write_text(json.dumps(result_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result_doc.items() if k != "pairs"}, indent=2, sort_keys=True))
    return result_doc


if __name__ == "__main__":
    analyze()

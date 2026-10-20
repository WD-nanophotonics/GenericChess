"""Plan-derived finite-panel completion bounds; preserves the pinned analyzer."""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2628/run"
OUT = RUN / "corrected-analysis.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(td_reward: int | None, initial_reward: int | None) -> tuple[int, int]:
    td = (-1, 1) if td_reward is None else (td_reward, td_reward)
    initial = (-1, 1) if initial_reward is None else (initial_reward, initial_reward)
    return td[0] - initial[1], td[1] - initial[0]


def expected_pairs(plan: dict, pool: dict) -> set[tuple[int, int, int, int]]:
    return {
        (rule, seed, root["family"], color)
        for rule in plan["domain"]["rules"]
        for seed in plan["seeds"]
        for root in pool["evaluation_roots"]
        if root["rule_index"] == rule
        for color in (0, 1)
    }


def analyze() -> dict:
    if OUT.exists():
        raise FileExistsError("corrected analysis is write-once")
    plan_path = RUN / "plan.json"
    reg_path = RUN / "registration.json"
    result_path = RUN / "eval-result.json"
    audit_path = RUN / "evaluation-audit.json"
    games_path = RUN / "eval-games.jsonl"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    pool_path = ROOT / "results/dev_aux/task2627/rule15-successor-root-pools.json"
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    pinned_analyzer = ROOT / "results/dev_aux/task2628/analyze.py"
    if result.get("status") != "COMPLETE" or result.get("missing") != 0:
        raise ValueError("analysis requires a complete evaluation; partial results stay partial")
    if audit.get("status") != "PASS_REGISTERED_SLOT_ACTUAL_TERMINAL_HISTORY_AND_CAP_AUDIT":
        raise ValueError("independent evaluation audit must pass before analysis")
    if (sha(plan_path) != reg["plan_sha256"]
            or sha(pool_path) != reg["root_pools_sha256"]
            or result.get("plan_sha256") != reg["plan_sha256"]
            or sha(pinned_analyzer) != reg["source_pins"]["results/dev_aux/task2628/analyze.py"]
            or audit.get("evaluation_result_sha256") != sha(result_path)):
        raise ValueError("plan or audited evaluation receipt hash mismatch")

    expected = expected_pairs(plan, pool)
    pair_count = len(expected)
    if result.get("completed_slots") != plan["evaluation"]["slots"]:
        raise ValueError("completed slot count differs from frozen plan")
    games: dict[tuple[int, int, int, int, str], dict] = {}
    with games_path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            slot = tuple(row["slot"])
            if slot in games:
                raise ValueError("duplicate evaluation slot")
            games[slot] = row
    endpoints = {"initial", "TDLeaf"}
    expected_slots = {(*pair, endpoint) for pair in expected for endpoint in endpoints}
    if set(games) != expected_slots:
        raise ValueError("evaluation slots differ from plan-derived paired panel")

    wdl = {endpoint: Counter() for endpoint in endpoints}
    rewards = {}
    for slot, row in games.items():
        pair, endpoint = slot[:4], slot[4]
        reward = row["reward"]
        if reward is not None and reward not in (-1, 0, 1):
            raise ValueError("reward outside actual terminal W/L/D")
        wdl[endpoint]["UNKNOWN" if reward is None else {-1: "LOSS", 0: "DRAW", 1: "WIN"}[reward]] += 1
        rewards[(pair, endpoint)] = reward
    audited_wdl = audit.get("WDL_by_endpoint", {})
    if any(audited_wdl.get(endpoint) != dict(wdl[endpoint]) for endpoint in endpoints):
        raise ValueError("W/L/D/UNKNOWN totals differ from independent history audit")

    rows = []
    lo = hi = exact = unknown = 0
    for pair in sorted(expected):
        td, initial = rewards[(pair, "TDLeaf")], rewards[(pair, "initial")]
        lower, upper = bounds(td, initial)
        lo += lower
        hi += upper
        if td is None or initial is None:
            unknown += 1
        else:
            exact += 1
        rows.append({"pair": list(pair), "TDLeaf_reward": td, "initial_reward": initial,
                     "difference_bounds": [lower, upper]})

    summary = {"strata": pair_count, "exact_pairs": exact, "unknown_pairs": unknown,
               "difference_sum_bounds": [lo, hi],
               "difference_mean_bounds_exact": [str(Fraction(lo, pair_count)), str(Fraction(hi, pair_count))],
               "difference_mean_bounds": [lo / pair_count, hi / pair_count]}
    result_doc = {
        "status": "PASS_PLAN_DERIVED_FINITE_ACTUAL_TERMINAL_COMPLETION_BOUNDS",
        "plan_sha256": sha(plan_path), "registration_sha256": sha(reg_path),
        "evaluation_result_sha256": sha(result_path), "evaluation_audit_sha256": sha(audit_path),
        "evaluation_games_sha256": sha(games_path), "registered_analyzer_sha256": sha(pinned_analyzer),
        "corrected_analyzer_sha256": sha(Path(__file__)), "slots": len(games),
        "WDL_by_endpoint": {key: dict(value) for key, value in wdl.items()},
        "TDLeaf_minus_initial": summary,
        "correction": "The pinned analyze.py has a stale 512-stratum assertion from a different panel. This supplemental consumer derives the denominator from the unchanged registered rules, seeds, roots and colors; no inputs, slots, samples or caps changed.",
        "unknown_policy": "Every nonactual endpoint remains UNKNOWN and ranges independently over [-1,+1]; no UNKNOWN is imputed as a draw.",
        "claim_scope": "Exact registered finite panel only; completion bounds are not confidence intervals or population effects.",
        "pairs": rows,
    }
    with OUT.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result_doc, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result_doc.items() if key != "pairs"}, indent=2, sort_keys=True))
    return result_doc


if __name__ == "__main__":
    analyze()

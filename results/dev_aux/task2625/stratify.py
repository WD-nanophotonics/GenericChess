"""Descriptive fixed-panel completion bounds by rule and seed."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent / "run"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(rows: list[dict]) -> dict:
    lo = hi = exact = unknown = 0
    for row in rows:
        td, initial = row["TDLeaf_reward"], row["initial_reward"]
        td_lo, td_hi = (-1, 1) if td is None else (td, td)
        in_lo, in_hi = (-1, 1) if initial is None else (initial, initial)
        lo += td_lo - in_hi
        hi += td_hi - in_lo
        if td is None or initial is None:
            unknown += 1
        else:
            exact += 1
    n = len(rows)
    if not n:
        raise ValueError("empty descriptive stratum")
    return {"pairs": n, "exact_pairs": exact, "unknown_pairs": unknown,
            "difference_sum_bounds": [lo, hi],
            "difference_mean_bounds": [lo / n, hi / n]}


def run() -> dict:
    analysis_path = RUN / "analysis.json"
    out = RUN / "stratified-bounds.json"
    if out.exists():
        raise FileExistsError("stratified analysis is write-once")
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    if analysis.get("status") != "PASS_FINITE_ACTUAL_TERMINAL_COMPLETION_BOUNDS":
        raise ValueError("requires the audited frozen-panel analysis")
    pairs = analysis["pairs"]
    by_rule: dict[str, list[dict]] = defaultdict(list)
    by_seed: dict[str, list[dict]] = defaultdict(list)
    for row in pairs:
        rule, seed, _family, _color = row["pair"]
        by_rule[str(rule)].append(row)
        by_seed[str(seed)].append(row)
    rules = {key: bounds(value) for key, value in sorted(by_rule.items())}
    seeds = {key: bounds(value) for key, value in sorted(by_seed.items())}
    if sum(v["pairs"] for v in rules.values()) != 512 or sum(v["pairs"] for v in seeds.values()) != 512:
        raise ValueError("unexpected finite-panel denominator")
    if [sum(v["difference_sum_bounds"][i] for v in rules.values()) for i in (0, 1)] != analysis["TDLeaf_minus_initial"]["difference_sum_bounds"]:
        raise ValueError("rule slices do not reconcile with registered aggregate")
    if [sum(v["difference_sum_bounds"][i] for v in seeds.values()) for i in (0, 1)] != analysis["TDLeaf_minus_initial"]["difference_sum_bounds"]:
        raise ValueError("seed slices do not reconcile with registered aggregate")
    result = {"status": "PASS_DESCRIPTIVE_STRATA_RECONCILE",
              "analysis_sha256": digest(analysis_path),
              "rules": rules, "seeds": seeds,
              "interpretation": "Descriptive finite-panel completion bounds only; crossed seeds and reused roots are dependent strata, not confidence intervals or population estimates."}
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    run()

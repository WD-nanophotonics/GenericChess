"""Exact finite matched W-L completion bounds for task2616; UNKNOWN is not draw."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json

TASK = Path(__file__).resolve().parent
ENDPOINTS = ("initial", "TD", "WDL", "TreeStrap")
CONTRASTS = (("TreeStrap", "initial"), ("TD", "initial"), ("WDL", "initial"),
             ("TreeStrap", "TD"), ("TreeStrap", "WDL"))

def reward_bounds(value):
    return (-1, 1) if value is None else (value, value)

def contrast(table, bases, left, right):
    low = high = 0
    counts = Counter()
    by_seed, by_color, by_family = defaultdict(list), defaultdict(list), defaultdict(list)
    for base in bases:
        a = table.get((*base, left))
        b = table.get((*base, right))
        alo, ahi = reward_bounds(a)
        blo, bhi = reward_bounds(b)
        interval = (alo - bhi, ahi - blo)
        low += interval[0]
        high += interval[1]
        counts["both_known"] += a is not None and b is not None
        counts["unknown_endpoint"] += a is None or b is None
        counts["missing_pair"] += (*base, left) not in table or (*base, right) not in table
        entry = {"base": base, "bounds": interval, "left_reward": a, "right_reward": b}
        by_seed[str(base[1])].append(entry)
        by_color[str(base[3])].append(entry)
        by_family[str(base[2])].append(entry)
    n = len(bases)
    return {
        "n_registered_pairs": n, "sum_bound": [low, high],
        "mean_bound": [low / max(1, n), high / max(1, n)],
        "counts": dict(counts),
        "by_seed_sum_bounds": {k: [sum(x["bounds"][0] for x in v), sum(x["bounds"][1] for x in v)] for k, v in by_seed.items()},
        "by_color_sum_bounds": {k: [sum(x["bounds"][0] for x in v), sum(x["bounds"][1] for x in v)] for k, v in by_color.items()},
        "by_family_sum_bounds": {k: [sum(x["bounds"][0] for x in v), sum(x["bounds"][1] for x in v)] for k, v in by_family.items()},
    }

def run(directory=None):
    d = TASK if directory is None else Path(directory)
    plan = json.loads((d / "eval-plan.json").read_text(encoding="utf-8"))
    result = json.loads((d / "eval-result.json").read_text(encoding="utf-8"))
    binding = json.loads((d / "eval-binding.json").read_text(encoding="utf-8"))
    if binding["assembled_result_sha256"] != hashlib.sha256((d / "result.json").read_bytes()).hexdigest():
        raise RuntimeError("evaluation/model binding mismatch")
    if binding["plan_sha256"] != hashlib.sha256((d / "eval-plan.json").read_bytes()).hexdigest():
        raise RuntimeError("evaluation plan binding mismatch")
    rows = [json.loads(line) for line in (d / "eval-games.jsonl").read_text(encoding="utf-8").splitlines() if line]
    table = {}
    wdl = defaultdict(Counter)
    for row in rows:
        slot = tuple(row["slot"])
        if slot in table:
            raise AssertionError(f"duplicate evaluation slot: {slot}")
        reward = row["reward"]
        if reward is not None and reward not in (-1, 0, 1):
            raise AssertionError(f"invalid reward: {reward}")
        normalized = (slot[0], slot[1], slot[2], slot[3], slot[5], slot[4])
        table[normalized] = reward
        endpoint = slot[4]
        wdl[endpoint]["UNKNOWN" if reward is None else {-1: "LOSS", 0: "DRAW", 1: "WIN"}[reward]] += 1
    slot_set = {(slot[0], slot[1], slot[2], slot[3], slot[5], slot[4]) for slot in plan["slots"]}
    if not set(table).issubset(slot_set):
        raise AssertionError("observed unregistered evaluation slot")
    bases = sorted({(s[0], s[1], s[2], s[3], s[5]) for s in plan["slots"]})
    # Table intentionally omits missing slots; get() maps both missing and UNKNOWN
    # to [-1,+1], while counts distinguish missing scheduled pairs.
    contrasts = {f"{left}-{right}": contrast(table, bases, left, right) for left, right in CONTRASTS}
    if len(table) != result["actual"] or result["missing"] != result["expected"] - result["actual"]:
        raise AssertionError("evaluation result counts do not match the saved slot rows")
    out = {
        "task": "DEV_AUX2616", "status": "COMPLETE_DERIVED_FINITE_PANEL" if result["missing"] == 0 else "PARTIAL_DERIVED_FINITE_PANEL",
        "evaluation_status": result["status"], "input_sha256": hashlib.sha256((d / "eval-games.jsonl").read_bytes()).hexdigest(),
        "observed_slots": len(table), "registered_slots": len(slot_set),
        "wdl_by_endpoint": {k: dict(v) for k, v in wdl.items()},
        "contrasts": contrasts,
        "limits": "Exact completion bounds for this registered finite panel, not confidence intervals/population effects. Only UNKNOWN/missing endpoint rewards vary in [-1,+1]; known rewards, including draws, remain fixed.",
        "training_outcomes_not_used_for_selection": True,
        "registered_denominator_per_pair": len(bases),
        "eval_result_sha256": hashlib.sha256((d / "eval-result.json").read_bytes()).hexdigest(),
    }
    (d / "summary.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out

if __name__ == "__main__": print(json.dumps(run(), indent=2))

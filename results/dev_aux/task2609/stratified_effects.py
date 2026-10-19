"""Descriptive, outcome-preserving subgroup bounds for the frozen panel."""
from pathlib import Path
from collections import defaultdict
import json

D = Path("results/dev_aux/task2609")
plan = json.loads((D / "eval-plan.json").read_text(encoding="utf-8"))
rows = [json.loads(line) for line in (D / "eval-games.jsonl").read_text(encoding="utf-8").splitlines()]
outcomes = {}
for row in rows:
    rule, seed, family, color, endpoint, _ = row["slot"]
    outcomes[(rule, seed, family, color, endpoint)] = row["reward"]

def measure(group_key, key_value):
    contrasts = {}
    for left, right in (("LocalLambda", "initial"), ("LocalLambda", "TD95"), ("TD95", "initial")):
        bounds, unknown = [], 0
        for rule in plan["rules"]:
            for seed in plan["seeds"]:
                if group_key == "rule" and rule != key_value:
                    continue
                if group_key == "seed" and seed != key_value:
                    continue
                for family in {slot[2] for slot in plan["slots"] if slot[0] == rule}:
                    for color in (0, 1):
                        a = outcomes[(rule, seed, family, color, left)]
                        b = outcomes[(rule, seed, family, color, right)]
                        if a is None or b is None:
                            bounds.append((-2, 2)); unknown += 1
                        else:
                            bounds.append((a-b, a-b))
        n = len(bounds)
        contrasts[f"{left}_minus_{right}"] = {
            "strata": n, "unknown_pairs": unknown,
            "mean_bound": [sum(x[0] for x in bounds)/n, sum(x[1] for x in bounds)/n],
        }
    return contrasts

result = {
    "scope": "Post-hoc descriptive subgrouping of the complete frozen task2609 panel. No model/parameter/seed/root selection; UNKNOWN pairs retain [-2,+2]. Subgroups share roots and are not independent inferential tests.",
    "by_rule": {str(rule): measure("rule", rule) for rule in plan["rules"]},
    "by_parameter_seed": {str(seed): measure("seed", seed) for seed in plan["seeds"]},
}
(D / "stratified-effects.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))

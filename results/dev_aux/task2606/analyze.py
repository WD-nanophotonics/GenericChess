"""Outcome-blind finite-panel audit for task2606; never imputes UNKNOWN as draw."""
from pathlib import Path
from collections import Counter, defaultdict
import json

D = Path("results/dev_aux/task2606")

def rows(path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def reward(outcome, color):
    return None if outcome is None else outcome * (1 if color == 0 else -1)

def main():
    plan = json.loads((D / "plan.json").read_text())
    train = json.loads((D / "result.json").read_text())
    eval_plan = json.loads((D / "eval-plan.json").read_text())
    eval_result = json.loads((D / "eval-result.json").read_text())
    training_games = list(rows(D / "games.jsonl"))
    queries = list(rows(D / "queries.jsonl"))
    eval_games = list(rows(D / "eval-games.jsonl"))
    endpoints = eval_plan["endpoints"]

    role_nodes = defaultdict(Counter)
    for r in queries:
        key = (r['generator_seed'], r['seed'], r['method'])
        role = 'candidate' if r['actor'] == r['color'] else 'fixed_opponent'
        role_nodes[key][role] += r['nodes']

# Audit the accounting and fixed-opponent execution path from raw query rows.
    arm_query_nodes = Counter()
    for q in queries:
        key = (q["generator_seed"], q["seed"], q["method"])
        arm_query_nodes[key] += q["nodes"]
        assert q["learner_actor"] == (q["actor"] == q["color"])
        assert q["observed"] == (q["complete"] and q["actor"] == q["color"])
        if not q["complete"]:
            assert q["record_after"] == q["record_before"]
    for arm in train["arms"]:
        key = (arm["generator_seed"], arm["seed"], arm["method"])
        assert arm_query_nodes[key] == arm["nodes"], (key, arm_query_nodes[key], arm["nodes"])
    if train["status"] == "COMPLETE":
        assert len(train["arms"]) == len(plan["arms_order"])
        assert train["nodes"] == plan["target_training_nodes"]
    execution_audit = "PASS"

    train_audit = {}
    for method in plan["methods"]:
        q = [r for r in queries if r["method"] == method]
        g = [r for r in training_games if r["method"] == method]
        train_audit[method] = {
            "paid_nodes": sum(r["nodes"] for r in train["arms"] if r["method"] == method),
            "games": len(g),
            "actual_terminal_games": sum(r["outcome"] is not None for r in g),
            "unknown_games": sum(r["outcome"] is None for r in g),
            "complete_observations": sum(bool(r["observed"]) for r in q),
            "terminal_pv_observations": sum(bool(r["observed"] and r["pv_terminal"]) for r in q),
            "incomplete_queries": sum(not r["complete"] for r in q),
            "incomplete_observations": sum(bool(r["observed"] and not r["complete"]) for r in q),
            "weights_by_rule_seed": [{"rule": a["generator_seed"], "seed": a["seed"], "weights": a["weights"], "total_nodes": a["nodes"], "candidate_nodes": role_nodes[(a["generator_seed"], a["seed"], method)]["candidate"], "fixed_opponent_nodes": role_nodes[(a["generator_seed"], a["seed"], method)]["fixed_opponent"]} for a in train["arms"] if a["method"] == method],
        }
    # Every trained arm must expose its original common initialization.
    initial_vectors = defaultdict(set)
    for arm in train["arms"]:
        initial_vectors[(arm["generator_seed"], arm["seed"])].add(tuple(arm["initial"]))
    expected_methods = set(plan["methods"])
    present_methods = defaultdict(set)
    for arm in train["arms"]:
        present_methods[(arm["generator_seed"], arm["seed"])].add(arm["method"])
    common_initialization = all(len(v) == 1 for v in initial_vectors.values()) and all(v == expected_methods for v in present_methods.values()) and len(present_methods) == len(plan["rules"]) * len(plan["seeds"])

    slot_rows = {}
    endpoint_counts = defaultdict(Counter)
    for r in eval_games:
        gs, seed, family, color, endpoint, foe = r["slot"]
        key = (gs, seed, family, color)
        slot_rows[(key, endpoint)] = r
        endpoint_counts[endpoint]["slots"] += 1
        if r["outcome"] is None:
            endpoint_counts[endpoint]["unknown"] += 1
        else:
            side_reward = reward(r["outcome"], color)
            endpoint_counts[endpoint]["actual_terminal"] += 1
            endpoint_counts[endpoint]["wins"] += side_reward == 1
            endpoint_counts[endpoint]["draws"] += side_reward == 0
            endpoint_counts[endpoint]["losses"] += side_reward == -1
            endpoint_counts[endpoint]["reward_sum"] += side_reward

    pairwise = {}
    stratum_rows = []
    for control in ("initial", "TD95"):
        deltas = []
        exact = []
        unknown_pairs = 0
        per_stratum = defaultdict(list)
        keys = sorted({(s[0], s[1], s[2], s[3]) for s in eval_plan["slots"]})
        for key in keys:
            cand = slot_rows.get((key, "LocalLambda"))
            base = slot_rows.get((key, control))
            if cand is None or base is None:
                unknown_pairs += 1
                deltas.append((-2.0, 2.0))
                per_stratum[key[:2]].append((-2.0, 2.0))
                continue
            cr = reward(cand["outcome"], key[3])
            br = reward(base["outcome"], key[3])
            if cr is None or br is None:
                unknown_pairs += 1
                bounds = (-2.0, 2.0)
            else:
                bounds = (cr - br, cr - br)
                exact.append(cr - br)
            deltas.append(bounds)
            per_stratum[key[:2]].append(bounds)
        pairwise[control] = {
            "pairs": len(deltas),
            "exact_pairs": len(exact),
            "unknown_or_missing_pairs": unknown_pairs,
            "finite_panel_mean_lower": sum(x[0] for x in deltas) / len(deltas) if deltas else None,
            "finite_panel_mean_upper": sum(x[1] for x in deltas) / len(deltas) if deltas else None,
        }
        for (gs, seed), values in sorted(per_stratum.items()):
            stratum_rows.append({"rule": gs, "seed": seed, "control": control,
                "pairs": len(values), "mean_lower": sum(x[0] for x in values) / len(values),
                "mean_upper": sum(x[1] for x in values) / len(values)})

    result = {
        "task": "DEV_AUX2606",
        "training_status": train["status"],
        "evaluation_status": eval_result["status"],
        "planned_arms": len(plan["arms_order"]),
        "completed_arms": len(train["arms"]),
        "planned_nodes": plan["target_training_nodes"],
        "paid_nodes": train["nodes"],
        "training_seconds": train["seconds"],
        "training_execution_audit": execution_audit,
        "training_by_method": train_audit,
        "initialization_common_within_stratum": common_initialization,
        "evaluation_expected": eval_result["expected"],
        "evaluation_actual": eval_result["actual"],
        "evaluation_missing": eval_result["missing"],
        "evaluation_nodes": eval_result["nodes"],
        "evaluation_seconds": eval_result["seconds"],
        "endpoint_outcomes": {k: dict(v) for k, v in endpoint_counts.items()},
        "LocalLambda_pairwise_bounds": pairwise,
        "per_rule_seed_bounds": stratum_rows,
        "interpretation": "Finite registered panel only. Each UNKNOWN/missing pair contributes [-2,+2] reward-difference bounds; never imputed as draw. No population confidence claim.",
    }
    (D / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("training_by_method", "per_rule_seed_bounds")}, indent=2))

if __name__ == "__main__":
    main()
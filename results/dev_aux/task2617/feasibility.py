"""Outcome-blind feasibility for a fresh Chess 20k-vs-40k cap panel.

This only builds a prospective plan. It never runs games, reads outcome fields,
or registers/starts the experiment.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "results/dev_aux/task2617"
sys.path.insert(0, str(ROOT))
from results.dev_aux.task2492.adapters import ChessEnv  # noqa: E402
from results.dev_aux.task2565.train import prefix  # noqa: E402


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical(record: dict) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    plan_2568_path = ROOT / "results/dev_aux/task2568/plan.json"
    plan_2568 = json.loads(plan_2568_path.read_text(encoding="utf-8"))
    assert plan_2568["domain"] == "chess" and plan_2568["prefix_plies"] == 8
    assert plan_2568["foe"] == [1.0] * 5

    # Read only the initial full Chess history from every registered Chess panel.
    # Outcomes, actions after the root, rewards and endpoint labels are ignored.
    registered_roots: set[str] = set()
    eval_plan_sources: list[dict] = []
    for eval_plan_path in sorted((ROOT / "results/dev_aux").rglob("eval-plan.json")):
        eval_plan = json.loads(eval_plan_path.read_text(encoding="utf-8"))
        if eval_plan.get("domain") != "chess" or 0 not in eval_plan.get("rules", []):
            continue
        games_path = eval_plan_path.parent / "eval-games.jsonl"
        if not games_path.exists():
            continue
        before = len(registered_roots)
        rows = 0
        for line in games_path.open(encoding="utf-8-sig"):
            row = json.loads(line)
            record = row.get("initial_record")
            if record is not None:
                registered_roots.add(canonical(record))
                rows += 1
        eval_plan_sources.append(
            {
                "plan": eval_plan_path.relative_to(ROOT).as_posix(),
                "plan_sha256": sha_file(eval_plan_path),
                "games": games_path.relative_to(ROOT).as_posix(),
                "games_sha256": sha_file(games_path),
                "rows_with_initial_record": rows,
                "new_unique_records": len(registered_roots) - before,
            }
        )

    # Reconstruct every possible 8-ply task2616 training-family root, not just
    # roots that happened to be visited in the completed training trace.
    train_families = range(
        plan_2568["training_family_offset"],
        plan_2568["training_family_offset"] + (plan_2568["max_games"] + 1) // 2,
    )
    all_task2616_training_roots: set[str] = set()
    for family in train_families:
        env = ChessEnv()
        prefix(env, 0, family, plan_2568["prefix_plies"])
        record = env.record()
        if len(record["moves"]) == plan_2568["prefix_plies"]:
            all_task2616_training_roots.add(canonical(record))

    prior_panel = json.loads(
        (ROOT / "results/dev_aux/task2616/root-manifest.json").read_text(encoding="utf-8")
    )
    prior_eval_roots = {canonical(row["record"]) for row in prior_panel["roots"]}

    selected: list[dict] = []
    seen: set[str] = set()
    examined_valid = 0
    for family in range(710001, 720001):
        env = ChessEnv()
        prefix(env, 0, family, 8)
        record = env.record()
        if len(record["moves"]) != 8:
            continue
        examined_valid += 1
        key = canonical(record)
        if (
            key in seen
            or key in registered_roots
            or key in all_task2616_training_roots
            or key in prior_eval_roots
        ):
            continue
        seen.add(key)
        selected.append(
            {
                "family": family,
                "record": record,
                "record_sha256": sha_bytes(key.encode("utf-8")),
            }
        )
        if len(selected) == 32:
            break
    assert len(selected) == 32

    # Balanced family-level randomization. All seeds/colors/endpoints under one
    # family share its cap so within-family method contrasts remain matched.
    rng_seed = 26170001
    rng = random.Random(rng_seed)
    family_ids = [row["family"] for row in selected]
    shuffled = family_ids[:]
    rng.shuffle(shuffled)
    high_cap = set(shuffled[:16])
    assignments = [
        {"family": family, "node_cap_both_sides": 40000 if family in high_cap else 20000}
        for family in family_ids
    ]
    assert sum(row["node_cap_both_sides"] == 20000 for row in assignments) == 16
    assert sum(row["node_cap_both_sides"] == 40000 for row in assignments) == 16
    slot_order_seed = 26170002
    execution_slot_order = [
        [family, seed, color, endpoint]
        for family in family_ids
        for seed in [1977, 8173, 27182, 31415]
        for color in (0, 1)
        for endpoint in ("initial", "TD", "WDL", "TreeStrap")
    ]
    random.Random(slot_order_seed).shuffle(execution_slot_order)
    assert len(execution_slot_order) == 1024
    assert len({tuple(slot) for slot in execution_slot_order}) == 1024

    task2568_training_sha = {sha_bytes(item.encode("utf-8")) for item in all_task2616_training_roots}
    assert task2568_training_sha == set(prior_panel["possible_train_root_sha256s"])
    chosen_sha = {row["record_sha256"] for row in selected}
    assert not chosen_sha & {sha_bytes(item.encode("utf-8")) for item in registered_roots}
    assert not chosen_sha & task2568_training_sha
    assert not chosen_sha & {sha_bytes(item.encode("utf-8")) for item in prior_eval_roots}

    eval_result_path = ROOT / "results/dev_aux/task2616/eval-result.json"
    eval_result = json.loads(eval_result_path.read_text(encoding="utf-8"))
    eval_nodes = eval_result["nodes"]
    eval_seconds = eval_result["seconds"]
    assert eval_nodes == 14648460
    max_node_total = 16 * 32 * 20000 + 16 * 32 * 40000
    linear_seconds = max_node_total / (eval_nodes / eval_seconds)
    risk_adjusted_search_seconds = linear_seconds * 1.25
    setup_audit_reserve_seconds = 900
    total_expected_seconds = risk_adjusted_search_seconds + setup_audit_reserve_seconds
    runtime_cap_seconds = 5400
    total_cap_plus_reserve_seconds = runtime_cap_seconds + setup_audit_reserve_seconds

    report = {
        "task": "DEV_AUX2617",
        "status": "FEASIBILITY_ONLY_NOT_REGISTERED_NOT_STARTED",
        "question": "On a fresh fixed-foe Chess panel, does raising the per-slot both-actor node cap from 20k to 40k reduce UNKNOWN and alter endpoint-specific actual-W/L contrasts?",
        "root_unit": "exact full ChessEnv record: initial FEN plus ordered 8-ply UCI history",
        "prefix_plies": 8,
        "root_family_range_searched": [710001, 720000],
        "valid_candidate_families_examined_until_32_selected": examined_valid,
        "registered_eval_unique_roots_excluded": len(registered_roots),
        "task2616_possible_training_roots_excluded": len(all_task2616_training_roots),
        "task2616_eval_roots_excluded": len(prior_eval_roots),
        "selected_roots": selected,
        "overlap_counts": {"all_registered_eval_roots": 0, "task2616_possible_training_roots": 0, "task2616_eval_roots": 0},
        "eval_plan_sources": eval_plan_sources,
        "protocol": {
            "endpoints": ["initial", "TD", "WDL", "TreeStrap"],
            "seeds": [1977, 8173, 27182, 31415],
            "colors": [0, 1],
            "foe": "uniform [1,1,1,1,1]",
            "slots": 32 * 4 * 2 * 4,
            "budget_randomization_unit": "family; balanced 16 families/cap; all endpoints/seeds/colors within a family share assignment",
            "budget_rng_seed": rng_seed,
            "budget_assignments": assignments,
            "slot_order_rng_seed": slot_order_seed,
            "execution_slot_order": execution_slot_order,
            "caps_nodes_both_actors_per_slot": [20000, 40000],
            "max_total_nodes": max_node_total,
            "unknown": "censored; preserve actual terminal W/D/L; completion bounds vary only UNKNOWN endpoint rewards over [-1,+1]",
            "analysis": "Report UNKNOWN rates and known W/D/L by cap/endpoint; finite-panel UNKNOWN completion bounds for within-cap learner contrasts and randomized cap-group differences. The deterministic root list is not a population sample or confidence interval.",
            "global_runtime_cap_seconds": runtime_cap_seconds,
        },
        "cost_estimate": {
            "source_result": "results/dev_aux/task2616/eval-result.json",
            "source_result_sha256": sha_file(eval_result_path),
            "observed_nodes": eval_nodes,
            "observed_evaluation_seconds": eval_seconds,
            "observed_node_rate_per_second": eval_nodes / eval_seconds,
            "linear_max-node_projection_seconds": linear_seconds,
            "risk_factor": 1.25,
            "risk_adjusted_search_seconds": risk_adjusted_search_seconds,
            "setup_and_audit_reserve_seconds": setup_audit_reserve_seconds,
            "risk_adjusted_all_in_seconds": total_expected_seconds,
            "hard_runtime_cap_plus_setup_audit_seconds": total_cap_plus_reserve_seconds,
            "threshold_seconds": 7200,
            "interpretation": "The expected projection uses the completed task2616 end-to-end evaluation rate, a 25% multiplicative risk margin and 15m setup/audit reserve. The 90m evaluation cap plus reserve bounds planned work at 105m, below the user's 120m consultation threshold; actual concurrent load and nonlinear search behavior remain timing limitations. Preserve missing slots if the cap binds.",
        },
        "sources": {
            path: sha_file(ROOT / path)
            for path in [
                "results/dev_aux/task2616/prepare.py",
                "results/dev_aux/task2616/evaluate.py",
                "results/dev_aux/task2616/eval-plan.json",
                "results/dev_aux/task2616/root-manifest.json",
                "results/dev_aux/task2568/plan.json",
                "results/dev_aux/task2616/eval-result.json",
                "results/dev_aux/task2492/adapters.py",
                "results/dev_aux/task2565/train.py",
                "results/dev_aux/task2617/feasibility.py",
            ]
        },
        "next_gate": "Before execution, implement and test a separate family-randomized evaluator and preregister its exact source hashes/assignment file. Do not alter task2616 or reuse its panel as the outcome test. The 105m cap includes 15m setup/audit and stays below 120m; if a revised estimate reaches 120m, consult Dot before starting that experiment.",
    }
    write_json(OUT / "prospective-roots.json", {"task": "DEV_AUX2617", "roots": selected})
    write_json(
        OUT / "execution-order.json",
        {"task": "DEV_AUX2617", "seed": slot_order_seed, "slots": execution_slot_order},
    )
    write_json(OUT / "feasibility.json", report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "selected_roots": len(selected),
                "overlap_counts": report["overlap_counts"],
                "slots": report["protocol"]["slots"],
                "max_nodes": max_node_total,
                "risk_adjusted_all_in_minutes": total_expected_seconds / 60,
                "hard_cap_plus_reserve_minutes": total_cap_plus_reserve_seconds / 60,
                "slot_order_count": len(execution_slot_order),
                "sources": report["sources"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

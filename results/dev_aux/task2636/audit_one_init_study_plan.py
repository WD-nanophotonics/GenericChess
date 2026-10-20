from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
import sys
import ast

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from results.dev_aux.task2625.freeze_study import initial_vector

PLAN_PATH = ROOT / "results/dev_aux/task2636/one-init-study-plan.json"
OUT_PATH = ROOT / "results/dev_aux/task2636/one-init-study-plan-audit.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def assigned_literals(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        found[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    return found


def main() -> None:
    plan = read(PLAN_PATH)
    proposed_run = ROOT / plan["proposed_execution_directory"]
    if proposed_run.exists():
        raise AssertionError("future run-v1 path is already present; design cannot claim a fresh one-shot directory")
    source_pins = plan["source_lineage"]
    checked = {
        "root_plan": ("root_plan", "root_plan_sha256"),
        "root_pool": ("root_pool", "root_pool_sha256"),
        "root_audit": ("root_audit", "root_audit_sha256"),
        "candidate_index": ("candidate_index", "candidate_index_sha256"),
        "task2625_reference_plan": ("task2625_reference_plan", "task2625_reference_plan_sha256"),
        "task2625_training_result": ("task2625_training_result", "task2625_training_result_sha256"),
        "task2625_evaluation_result": ("task2625_evaluation_result", "task2625_evaluation_result_sha256"),
        "task2635_cost_basis": ("task2635_cost_basis", "task2635_cost_basis_sha256"),
        "task2625_training": ("task2625_reference_plan", None),
    }
    hashes = {
        key: sha(ROOT / source_pins[path_key])
        for key, (path_key, _) in checked.items()
        if key != "task2625_training"
    }
    code_paths = {
        "task2625_training_source_sha256": "results/dev_aux/task2625/train.py",
        "task2625_evaluation_source_sha256": "results/dev_aux/task2625/evaluate.py",
        "task2625_training_audit_source_sha256": "results/dev_aux/task2625/audit_training.py",
        "task2625_evaluation_audit_source_sha256": "results/dev_aux/task2625/audit_evaluation.py",
        "task2625_analysis_source_sha256": "results/dev_aux/task2625/analyze.py",
        "task2625_training_result_sha256": "results/dev_aux/task2625/run/training-result.json",
        "task2625_evaluation_result_sha256": "results/dev_aux/task2625/run/eval-result.json",
        "task2635_cost_basis_sha256": "results/dev_aux/task2635/NEXT-LEARNER-PANEL-BUDGET.md",
        "task2625_initial_vector_source_sha256": "results/dev_aux/task2625/freeze_study.py",
        "task2621_fixed_scale_adapter_sha256": "results/dev_aux/task2621/fixed_scale.py",
        "task2492_search_and_learner_sha256": "results/dev_aux/task2492/learning.py",
        "task2392_stop_reader_sha256": "results/dev_aux/task2392/reader.py",
        "task2511_generic_terminal_adapter_sha256": "results/dev_aux/task2511/generic.py",
        "task2636_root_runner_sha256": "results/dev_aux/task2636/prepare_one_init_roots.py",
        "task2636_design_audit_source_sha256": "results/dev_aux/task2636/audit_one_init_study_plan.py",
    }
    for key, rel in code_paths.items():
        hashes[key] = sha(ROOT / rel)
        if hashes[key] != source_pins[key]:
            raise AssertionError(f"source pin mismatch: {rel}")
    for key, (path_key, hash_key) in checked.items():
        if hash_key and hashes[key] != source_pins[hash_key]:
            raise AssertionError(f"source pin mismatch: {source_pins[path_key]}")

    pool = read(ROOT / source_pins["root_pool"])
    root_audit = read(ROOT / source_pins["root_audit"])
    root_plan = read(ROOT / source_pins["root_plan"])
    reference = read(ROOT / source_pins["task2625_reference_plan"])
    old_train_result = read(ROOT / source_pins["task2625_training_result"])
    old_eval_result = read(ROOT / source_pins["task2625_evaluation_result"])
    measured = plan["budget"]["task2625_measured_reference"]
    if old_train_result["seconds"] != measured["training_seconds"] or old_train_result["nodes"] != measured["training_nodes"] or old_train_result["episodes"] != measured["training_episodes"]:
        raise AssertionError("task2625 training benchmark differs from its pinned receipt")
    if old_eval_result["seconds"] != measured["evaluation_seconds"] or old_eval_result["nodes"] != measured["evaluation_nodes"] or old_eval_result["completed_slots"] != measured["evaluation_slots"] or old_eval_result["UNKNOWN"] != measured["evaluation_unknown"] or old_eval_result["missing"] != measured["evaluation_missing"]:
        raise AssertionError("task2625 evaluation benchmark differs from its pinned receipt")
    old_train_source = ROOT / code_paths["task2625_training_source_sha256"]
    old_eval_source = ROOT / code_paths["task2625_evaluation_source_sha256"]
    old_train_constants = assigned_literals(old_train_source)
    old_eval_constants = assigned_literals(old_eval_source)
    old_train_audit_text = (ROOT / code_paths["task2625_training_audit_source_sha256"]).read_text(encoding="utf-8")
    old_eval_audit_text = (ROOT / code_paths["task2625_evaluation_audit_source_sha256"]).read_text(encoding="utf-8")
    old_analysis_text = (ROOT / code_paths["task2625_analysis_source_sha256"]).read_text(encoding="utf-8")
    search_text = (ROOT / code_paths["task2492_search_and_learner_sha256"]).read_text(encoding="utf-8")
    stop_reader_text = (ROOT / code_paths["task2392_stop_reader_sha256"]).read_text(encoding="utf-8")
    if root_audit["status"] != "PASS_SOURCE_PREFIX_HISTORY_FEATURE_REPLAY_AND_SPLIT_AUDIT":
        raise AssertionError("task2636 root pool audit did not pass")
    if root_audit["training_or_evaluation_started"] or pool["learner_or_search_started"]:
        raise AssertionError("root preparation unexpectedly launched learning or evaluation")
    if pool["root_pool_registered"]:
        raise AssertionError("design must not register the pool")
    if tuple(old_train_constants.get("RULES", ())) != (271001, 271002, 271003, 271004):
        raise AssertionError("the pinned task2625 trainer rule grid changed")
    if tuple(old_train_constants.get("SEEDS", ())) != (1977, 8173, 27182, 31415):
        raise AssertionError("the pinned task2625 trainer seed grid changed")
    if tuple(old_eval_constants.get("ENDPOINTS", ())) != ("initial", "TDLeaf"):
        raise AssertionError("the pinned task2625 evaluation endpoints changed")
    if set(pool["training_roots"][0]) != {"candidate_index", "candidate_seed", "family", "channels", "features", "record", "record_sha256", "rule_path", "rule_sha256", "ruleset_fingerprint"}:
        raise AssertionError("task2636 root schema changed; redo runner contract review")
    if "rule" not in read(ROOT / "results/dev_aux/task2624/root-pools-v2.json")["training_roots"][0]:
        raise AssertionError("task2625 reference root schema changed")
    if reference["training"]["hard_seconds"] != 2400 or reference["evaluation"]["hard_seconds"] != 3600:
        raise AssertionError("task2625 reference phase-cap basis changed")
    original_cap_sum = (
        reference["training"]["hard_seconds"]
        + reference["evaluation"]["hard_seconds"]
        + plan["budget"]["lifetime_stage_hard_caps_seconds"]["preparation_audit_and_reporting_reserve"]
    )
    if original_cap_sum != 7200 or original_cap_sum <= plan["budget"]["global_hard_cap_seconds"]:
        raise AssertionError("the documented original phase-cap overrun changed")
    if 'result["status"] != "COMPLETE"' not in old_train_audit_text:
        raise AssertionError("task2625 training audit partial-run restriction changed")
    if 'result["status"] != "COMPLETE"' not in old_eval_audit_text or 'result["missing"] != 0' not in old_eval_audit_text:
        raise AssertionError("task2625 evaluation audit partial-run restriction changed")
    if 'result.get("status") != "COMPLETE"' not in old_analysis_text:
        raise AssertionError("task2625 analyzer partial-run restriction changed")
    if "if count%128==0:cancel()" not in search_text or "except BudgetEnd as e:" not in search_text:
        raise AssertionError("pinned AlphaBeta cancellation behavior changed")
    if "if stopped:raise PersistentStop" not in stop_reader_text:
        raise AssertionError("pinned persistent-stop behavior changed")
    candidate_rule_hashes = root_plan["candidate_rule_sha256"]
    for rel, expected in candidate_rule_hashes.items():
        if sha(ROOT / rel) != expected:
            raise AssertionError(f"candidate rule source pin mismatch: {rel}")

    rules = sorted({row["candidate_index"] for row in pool["training_roots"]})
    if rules != list(range(16)):
        raise AssertionError("the frozen pool does not contain exactly 16 candidate indexes")
    expected_channels = None
    coverage = {"training": {}, "evaluation": {}}
    caps = {}
    for candidate in rules:
        train = [r for r in pool["training_roots"] if r["candidate_index"] == candidate]
        evaluation = [r for r in pool["evaluation_roots"] if r["candidate_index"] == candidate]
        if len(train) != 120 or len(evaluation) != 16:
            raise AssertionError(f"candidate {candidate}: root count differs from design")
        channel_orders = {tuple(tuple(ch) for ch in r["channels"]) for r in train + evaluation}
        if len(channel_orders) != 1:
            raise AssertionError(f"candidate {candidate}: channel order differs across roots")
        channels = next(iter(channel_orders))
        if len(channels) != 10:
            raise AssertionError(f"candidate {candidate}: expected ten fixed-scale channels")
        if expected_channels is None:
            expected_channels = channels
        elif channels != expected_channels:
            raise AssertionError("candidate channel order differs across rules")
        if not all(len(r["features"]) == len(channels) for r in train + evaluation):
            raise AssertionError(f"candidate {candidate}: feature dimension mismatch")
        for label, rows in (("training", train), ("evaluation", evaluation)):
            active = {i for row in rows for i, value in enumerate(row["features"]) if value != 0}
            coverage[label][str(candidate)] = len(active)
        candidate_seed = train[0]["candidate_seed"]
        families = sorted(r["family"] for r in evaluation)
        shuffled = list(families)
        random.Random(977422 + candidate_seed).shuffle(shuffled)
        caps[str(candidate)] = {
            str(family): (20000 if i < 8 else 40000)
            for i, family in enumerate(shuffled)
        }
        if sum(value == 20000 for value in caps[str(candidate)].values()) != 8:
            raise AssertionError("evaluation cap assignment is not balanced")

    weights = initial_vector(1977, len(expected_channels))
    if len(weights) != 10 or weights[0] != 1.0:
        raise AssertionError("fixed-scale initialization has an unexpected dimension/anchor")
    if reference["training"]["nodes_per_arm_candidate_plus_foe"] * 16 != 4_000_000:
        raise AssertionError("aggregate training node budget changed")
    expected_slots = 16 * 1 * 16 * 2 * 2
    if expected_slots != 1024 or plan["evaluation"]["slots"] != expected_slots:
        raise AssertionError("evaluation slot arithmetic mismatch")
    if plan["evaluation"]["paired_root_color_contrasts"] != 16 * 16 * 2:
        raise AssertionError("paired contrast arithmetic mismatch")
    budget = plan["budget"]
    stage_sum = sum(budget["lifetime_stage_hard_caps_seconds"].values())
    if stage_sum != budget["global_hard_cap_seconds"] or stage_sum != 6600:
        raise AssertionError("phase caps do not fit the global hard ceiling")
    if budget["lifetime_stage_hard_caps_seconds"]["evaluation"] != 3000:
        raise AssertionError("evaluation cap does not close the 6600-second budget")
    if abs(budget["completed_preparation_audit_budget_charge_seconds"] + budget["remaining_preparation_audit_reporting_budget_seconds"] - 1200) > 1e-6:
        raise AssertionError("preparation/audit/reporting reserve accounting is inconsistent")
    if abs(budget["remaining_future_budget_seconds"] - (budget["lifetime_stage_hard_caps_seconds"]["training"] + budget["lifetime_stage_hard_caps_seconds"]["evaluation"] + budget["remaining_preparation_audit_reporting_budget_seconds"])) > 1e-6:
        raise AssertionError("remaining future budget is inconsistent")
    expected = sum(
        budget["projected_seconds"][key]
        for key in ("training", "evaluation", "preparation_audit_reporting_reserve")
    )
    if abs(expected - budget["projected_seconds"]["all_in"]) > 1e-6:
        raise AssertionError("projected budget components do not add up")
    margins = {
        "training_seconds": budget["lifetime_stage_hard_caps_seconds"]["training"] - budget["projected_seconds"]["training"],
        "evaluation_seconds": budget["lifetime_stage_hard_caps_seconds"]["evaluation"] - budget["projected_seconds"]["evaluation"],
        "all_in_seconds": budget["global_hard_cap_seconds"] - budget["projected_seconds"]["all_in"],
    }
    if plan["state"] != "DESIGN_ONLY_NOT_REGISTERED_NO_TRAINING_OR_EVALUATION":
        raise AssertionError("design state must remain unregistered")
    if plan["partial_semantics"]["analysis_denominator"].find("512 predeclared") < 0:
        raise AssertionError("partial analysis must retain the full predeclared pair denominator")
    if plan["cancellation_contract"]["global_deadline"].find("6057.368 seconds") < 0:
        raise AssertionError("global cancellation contract lost its remaining budget")

    report = {
        "status": "PASS_SOURCE_HASH_METHOD_ROOT_CHANNEL_BUDGET_AND_SLOT_DESIGN_AUDIT",
        "plan_sha256": sha(PLAN_PATH),
        "source_sha256": hashes,
        "candidate_rule_sha256": candidate_rule_hashes,
        "candidate_count": len(rules),
        "runner_contract": {
            "reference_train_rules": list(old_train_constants["RULES"]),
            "reference_train_seeds": list(old_train_constants["SEEDS"]),
            "reference_eval_endpoints": list(old_eval_constants["ENDPOINTS"]),
            "reference_training_hard_seconds": reference["training"]["hard_seconds"],
            "reference_evaluation_hard_seconds": reference["evaluation"]["hard_seconds"],
            "reference_plus_reserve_cap_sum_seconds": original_cap_sum,
            "task2636_requires_new_candidate_index_runner": True,
            "task2636_cumulative_deadline_required": True,
            "task2625_auditors_accept_partial_results": False,
            "task2625_analyzer_accepts_partial_results": False,
            "task2636_partial_auditors_required": True,
            "missing_slots_remain_distinct_from_completed_unknown": True,
            "alpha_beta_cancel_poll_nodes": 128,
            "alpha_beta_budgetend_returns_incomplete_receipt": True,
            "persistent_stop_raises_outside_search": True,
            "future_runner_must_close_partial_output_before_stopping": True,
        },
        "training_roots": len(pool["training_roots"]),
        "evaluation_roots": len(pool["evaluation_roots"]),
        "channel_count": len(expected_channels),
        "channel_order_shared_across_all_roots": True,
        "initialization_seed": 1977,
        "initial_weight_dimension": len(weights),
        "initial_weights": weights,
        "training_node_cap": 4_000_000,
        "evaluation_slots": expected_slots,
        "paired_root_color_contrasts": plan["evaluation"]["paired_root_color_contrasts"],
        "training_rules_missing_any_root_channel": sum(v < 10 for v in coverage["training"].values()),
        "evaluation_rules_missing_any_root_channel": sum(v < 10 for v in coverage["evaluation"].values()),
        "minimum_training_root_channels": min(coverage["training"].values()),
        "minimum_evaluation_root_channels": min(coverage["evaluation"].values()),
        "planned_node_caps_by_candidate": caps,
        "lifetime_stage_hard_caps_seconds": budget["lifetime_stage_hard_caps_seconds"],
        "completed_preparation_audit_budget_charge_seconds": budget["completed_preparation_audit_budget_charge_seconds"],
        "remaining_preparation_audit_reporting_budget_seconds": budget["remaining_preparation_audit_reporting_budget_seconds"],
        "remaining_future_budget_seconds": budget["remaining_future_budget_seconds"],
        "lifetime_stage_caps_sum_seconds": stage_sum,
        "projected_all_in_seconds": budget["projected_seconds"]["all_in"],
        "projected_cap_margins_seconds": margins,
        "task2625_measured_reference": measured,
        "training_or_evaluation_started": False,
        "root_pool_registered": False,
        "proposed_run_directory_exists": proposed_run.exists(),
        "limitations": plan["root_limits"],
    }
    OUT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"source_sha256", "planned_node_caps_by_candidate", "limitations"}}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

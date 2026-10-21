"""Outcome-blind two-ply legal-action expansion on frozen root subsets."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
TASK = ROOT / "results/dev_aux/task2636"
OUTPUT = TASK / "depth2-legal-action-expansion-audit.json"
SUBSET_PER_CANDIDATE = 8


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    return raw, json.loads(raw)


def compile_source(path: Path, expected_sha: str):
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.schema import ruleset_from_dict

    raw = path.read_bytes()
    if sha(raw) != expected_sha:
        raise ValueError(f"rules source hash mismatch: {path.relative_to(ROOT)}")
    return compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))


def describe(values: list[int]) -> dict[str, float | int]:
    ordered = sorted(values)
    return {
        "roots": len(ordered),
        "min": ordered[0],
        "median": statistics.median(ordered),
        "mean": statistics.fmean(ordered),
        "p90_nearest_rank": ordered[math.ceil(0.9 * len(ordered)) - 1],
        "max": ordered[-1],
    }


def expand(rows: list[tuple[str, int, dict]], compiled: dict[str, object]) -> dict:
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.session.session import GameSession
    from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

    roots, first_ply_edges, second_ply_edges = [], [], []
    for group, _family, record in rows:
        env = FixedScaleSessionEnv(GameSession.replay(
            compiled[group], deserialize_game_record(json.dumps(record, separators=(",", ":")))))
        if env.record() != record:
            raise ValueError("root full-history replay mismatch")
        actions = env.actions()
        if not actions:
            raise ValueError("selected root has no legal action")
        child_edges = 0
        for action in actions:
            child = FixedScaleSessionEnv(GameSession.replay(
                compiled[group], deserialize_game_record(json.dumps(record, separators=(",", ":")))))
            child.push(action)
            child_edges += len(child.actions())
        roots.append({"group": group, "family": _family,
                      "root_legal_actions": len(actions),
                      "child_legal_action_sum": child_edges,
                      "child_positions": len(actions)})
        first_ply_edges.append(len(actions))
        second_ply_edges.append(child_edges)
    return {
        "selected_roots": len(roots),
        "root_legal_actions": describe(first_ply_edges),
        "child_position_legal_action_sum": describe(second_ply_edges),
        "mean_child_actions_per_root_action": sum(second_ply_edges) / sum(first_ply_edges),
        "mean_unpruned_two_ply_edges_per_root": statistics.fmean(
            a + b for a, b in zip(first_ply_edges, second_ply_edges)),
        "by_group": {
            group: {
                "roots": len(group_rows),
                "mean_root_actions": statistics.fmean(r["root_legal_actions"] for r in group_rows),
                "mean_child_action_sum": statistics.fmean(r["child_legal_action_sum"] for r in group_rows),
                "mean_unpruned_two_ply_edges": statistics.fmean(
                    r["root_legal_actions"] + r["child_legal_action_sum"] for r in group_rows),
            }
            for group in sorted({r["group"] for r in roots})
            for group_rows in [[r for r in roots if r["group"] == group]]
        },
    }


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once output already exists: {OUTPUT}")
    plan_raw, plan = load(TASK / "one-init-study-plan.json")
    pool_raw, pool = load(ROOT / plan["source_lineage"]["root_pool"])
    index_raw, index = load(ROOT / plan["source_lineage"]["candidate_index"])
    if sha(pool_raw) != plan["source_lineage"]["root_pool_sha256"]:
        raise ValueError("task2636 root-pool hash mismatch")
    if sha(index_raw) != plan["source_lineage"]["candidate_index_sha256"]:
        raise ValueError("task2636 candidate-index hash mismatch")
    if pool["root_pool_registered"] or pool["learner_or_search_started"] or (TASK / "run-v1").exists():
        raise ValueError("branching audit requires the unregistered frozen study")

    candidate_rules = {
        str(i): compile_source(ROOT / row["source_file"], row["ruleset_sha256"])
        for i, row in enumerate(index["rows"])
    }
    candidate_train = []
    candidate_eval = []
    for candidate in range(len(index["rows"])):
        trains = sorted((r for r in pool["training_roots"] if r["candidate_index"] == candidate),
                        key=lambda r: r["family"])
        evals = sorted((r for r in pool["evaluation_roots"] if r["candidate_index"] == candidate),
                       key=lambda r: r["family"])
        if len(trains) != 120 or len(evals) != 16:
            raise ValueError("frozen root count changed")
        candidate_train.extend((str(candidate), r["family"], r["record"])
                               for r in trains[:SUBSET_PER_CANDIDATE])
        candidate_eval.extend((str(candidate), r["family"], r["record"])
                              for r in evals[:SUBSET_PER_CANDIDATE])

    old_plan_raw, old_plan = load(ROOT / "results/dev_aux/task2625/run/plan.json")
    old_pins = old_plan["source_pins"]
    old_rules = {
        str(rule): compile_source(ROOT / f"results/dev_aux/task2525/rules-{rule}.json",
                                  old_pins[f"results/dev_aux/task2525/rules-{rule}.json"])
        for rule in (271001, 271002, 271003, 271004)
    }
    train_manifest_raw, train_manifest = load(
        ROOT / "results/dev_aux/task2621/active-feature-probe/root-manifest.json")
    train_reg_raw, train_reg = load(ROOT / "results/dev_aux/task2621/cost-scan/registration.json")
    if sha(train_manifest_raw) != train_reg["root_manifest_sha256"]:
        raise ValueError("task2621 root manifest mismatch")
    ref_train = [(str(r["rule"]), r["family"], r["record"]) for r in train_manifest["roots"]]

    eval_plan_raw, eval_plan = load(ROOT / "results/dev_aux/task2609/eval-plan.json")
    eval_reg_raw, eval_reg = load(ROOT / "results/dev_aux/task2609/registration.json")
    eval_manifest_raw, eval_manifest = load(ROOT / "results/dev_aux/task2609/root-manifest.json")
    if sha(eval_manifest_raw) != eval_plan["root_manifest_sha256"] or sha(eval_manifest_raw) != eval_reg["root_manifest_sha256"]:
        raise ValueError("task2609 evaluation root-manifest mismatch")
    ref_eval = []
    for composite, record in sorted(eval_manifest["roots"].items()):
        rule, family = composite.split(":", 1)
        ref_eval.append((rule, int(family), record))

    result = {
        "status": "PASS_DEPTH2_LEGAL_ACTION_CENSUS_NO_SEARCH_NO_OUTCOME_READ",
        "source_script_sha256": sha(Path(__file__).read_bytes()),
        "pins": {
            "task2636_plan_sha256": sha(plan_raw),
            "task2636_root_pool_sha256": sha(pool_raw),
            "task2636_candidate_index_sha256": sha(index_raw),
            "task2625_reference_plan_sha256": sha(old_plan_raw),
            "task2621_training_manifest_sha256": sha(train_manifest_raw),
            "task2621_registration_sha256": sha(train_reg_raw),
            "task2609_evaluation_plan_sha256": sha(eval_plan_raw),
            "task2609_registration_sha256": sha(eval_reg_raw),
            "task2609_evaluation_manifest_sha256": sha(eval_manifest_raw),
        },
        "selection": f"lowest {SUBSET_PER_CANDIDATE} numeric family IDs per task2636 candidate, fixed before action counting; all pinned task2621 training roots and task2609 evaluation roots",
        "task2636_training": expand(candidate_train, candidate_rules),
        "task2621_training_basis": expand(ref_train, old_rules),
        "task2636_evaluation": expand(candidate_eval, candidate_rules),
        "task2609_evaluation_basis": expand(ref_eval, old_rules),
        "execution_state": {"run_v1_exists": (TASK / "run-v1").exists(),
                            "root_pool_registered": pool["root_pool_registered"],
                            "learner_or_search_started": pool["learner_or_search_started"]},
        "interpretation_limit": (
            "Full-history legal-action generation through two plies at fixed roots only. "
            "No AlphaBeta search, pruning, model, query, W/L/D or runtime extrapolation. "
            "Task2636 uses the first eight frozen family IDs per candidate, not all roots."
        ),
    }
    if any(result["execution_state"].values()):
        raise ValueError("execution started during read-only branching census")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()

"""Compare fixed-root unpruned D2 node-call upper bounds with the query cap."""
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
OUTPUT = TASK / "query-cap-screen.json"
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


def screen(rows: list[tuple[str, int, dict]], compiled: dict[str, object], cap: int) -> dict:
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.session.session import GameSession
    from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

    values: dict[str, list[int]] = {}
    for group, family, record in rows:
        env = FixedScaleSessionEnv(GameSession.replay(
            compiled[group], deserialize_game_record(json.dumps(record, separators=(",", ":")))))
        if env.record() != record:
            raise ValueError("root full-history replay mismatch")
        root_actions = env.actions()
        if not root_actions:
            raise ValueError("selected root has no legal action")
        child_reply_sum = 0
        for action in root_actions:
            child = FixedScaleSessionEnv(GameSession.replay(
                compiled[group], deserialize_game_record(json.dumps(record, separators=(",", ":")))))
            child.push(action)
            child_reply_sum += len(child.actions())
        # One root walk call, one call per root action, one per legal reply.
        # This is a no-pruning, no-terminal-shortcut upper-bound tree size.
        potential = 1 + len(root_actions) + child_reply_sum
        values.setdefault(group, []).append(potential)

    flattened = [n for group_values in values.values() for n in group_values]
    ordered = sorted(flattened)
    return {
        "selected_roots": len(ordered),
        "query_node_cap": cap,
        "full_width_nodes_gt_cap": sum(n > cap for n in ordered),
        "full_width_nodes_le_cap": sum(n <= cap for n in ordered),
        "fraction_gt_cap": sum(n > cap for n in ordered) / len(ordered),
        "full_width_node_calls": {
            "min": ordered[0], "median": statistics.median(ordered),
            "mean": statistics.fmean(ordered),
            "p90_nearest_rank": ordered[math.ceil(0.90 * len(ordered)) - 1],
            "max": ordered[-1],
        },
        "by_group": {
            group: {"roots": len(group_values), "gt_cap": sum(n > cap for n in group_values),
                    "mean_full_width_node_calls": statistics.fmean(group_values),
                    "max_full_width_node_calls": max(group_values)}
            for group, group_values in sorted(values.items())
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
        raise ValueError("query-cap screen requires the unregistered frozen study")

    candidate_rules = {str(i): compile_source(ROOT / row["source_file"], row["ruleset_sha256"])
                       for i, row in enumerate(index["rows"])}
    candidate_rows = []
    for candidate in range(len(index["rows"])):
        roots = sorted((r for r in pool["training_roots"] if r["candidate_index"] == candidate),
                       key=lambda r: r["family"])
        if len(roots) != 120:
            raise ValueError("frozen training-root count changed")
        candidate_rows.extend((str(candidate), r["family"], r["record"])
                              for r in roots[:SUBSET_PER_CANDIDATE])

    ref_plan_raw, ref_plan = load(ROOT / "results/dev_aux/task2625/run/plan.json")
    ref_rules = {str(rule): compile_source(ROOT / f"results/dev_aux/task2525/rules-{rule}.json",
                   ref_plan["source_pins"][f"results/dev_aux/task2525/rules-{rule}.json"])
                 for rule in (271001, 271002, 271003, 271004)}
    ref_manifest_raw, ref_manifest = load(ROOT / "results/dev_aux/task2621/active-feature-probe/root-manifest.json")
    ref_registration_raw, ref_registration = load(ROOT / "results/dev_aux/task2621/cost-scan/registration.json")
    if sha(ref_manifest_raw) != ref_registration["root_manifest_sha256"]:
        raise ValueError("task2621 cost-scan root manifest mismatch")
    ref_rows = [(str(r["rule"]), r["family"], r["record"]) for r in ref_manifest["roots"]]
    cap = plan["training"]["search"]["nodes_per_query"]
    result = {
        "status": "PASS_UNPRUNED_D2_QUERY_CAP_SCREEN_NO_SEARCH_NO_OUTCOME_READ",
        "source_script_sha256": sha(Path(__file__).read_bytes()),
        "pins": {
            "task2636_plan_sha256": sha(plan_raw),
            "task2636_pool_sha256": sha(pool_raw),
            "task2636_candidate_index_sha256": sha(index_raw),
            "task2625_reference_plan_sha256": sha(ref_plan_raw),
            "task2621_manifest_sha256": sha(ref_manifest_raw),
            "task2621_registration_sha256": sha(ref_registration_raw),
        },
        "selection": f"first {SUBSET_PER_CANDIDATE} numeric family IDs per candidate, fixed before counting; all8 task2621 reference roots",
        "task2636_training_subset": screen(candidate_rows, candidate_rules, cap),
        "task2621_training_basis": screen(ref_rows, ref_rules, cap),
        "execution_state": {"run_v1_exists": (TASK / "run-v1").exists(),
                            "root_pool_registered": pool["root_pool_registered"],
                            "learner_or_search_started": pool["learner_or_search_started"]},
        "interpretation_limit": (
            "Potential full-width walk-call count 1 + root actions + all child replies, "
            "ignoring alpha-beta cutoffs and terminal short-circuits. Exceeding 2,048 "
            "does not mean the actual search will hit its cap; it is not a cap-hit or UNKNOWN rate."
        ),
    }
    if any(result["execution_state"].values()):
        raise ValueError("execution started during no-search screen")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()

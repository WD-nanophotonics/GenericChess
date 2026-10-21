"""Outcome-blind legal-root branching census for frozen task2636 vs task2625."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession

TASK = ROOT / "results/dev_aux/task2636"
OUTPUT = TASK / "root-branching-cost-audit.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def quantile(values: list[int], fraction: float) -> int:
    return sorted(values)[max(0, math.ceil(fraction * len(values)) - 1)]


def summarize(values: list[int]) -> dict[str, float | int]:
    return {
        "roots": len(values),
        "min": min(values),
        "p50": statistics.median(values),
        "mean": statistics.fmean(values),
        "p90_nearest_rank": quantile(values, 0.90),
        "max": max(values),
    }


def load_compiled(rule_path: Path, expected_sha: str):
    raw = rule_path.read_bytes()
    if sha(raw) != expected_sha:
        raise ValueError(f"rule hash mismatch: {rule_path.relative_to(ROOT)}")
    return compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))


def count_roots(rows: list[dict], key_field: str, compiled_by: dict) -> tuple[dict, list[int]]:
    by_group: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        key = row[key_field]
        compiled = compiled_by[key]
        record = row["record"]
        session = GameSession.replay(
            compiled, deserialize_game_record(json.dumps(record, separators=(",", ":")))
        )
        if session.to_record().ruleset_fingerprint != record["ruleset_fingerprint"]:
            raise ValueError("root full-history fingerprint mismatch")
        count = len(session.legal_actions())
        if count <= 0:
            raise ValueError("frozen ongoing root has no legal action")
        by_group[str(key)].append(count)
    return {key: summarize(values) for key, values in sorted(by_group.items())}, [v for xs in by_group.values() for v in xs]


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once output already exists: {OUTPUT}")
    began = time.perf_counter()
    plan_raw = (TASK / "one-init-study-plan.json").read_bytes()
    plan = json.loads(plan_raw)
    lineage = plan["source_lineage"]
    candidate_index_path = ROOT / lineage["candidate_index"]
    candidate_raw = candidate_index_path.read_bytes()
    if sha(candidate_raw) != lineage["candidate_index_sha256"]:
        raise ValueError("candidate-index pin mismatch")
    root_pool_path = ROOT / lineage["root_pool"]
    root_pool_raw = root_pool_path.read_bytes()
    if sha(root_pool_raw) != lineage["root_pool_sha256"]:
        raise ValueError("task2636 root-pool pin mismatch")
    candidate_index = json.loads(candidate_raw)
    roots = json.loads(root_pool_raw)
    candidate_rules = {
        index: load_compiled(ROOT / row["source_file"], row["ruleset_sha256"])
        for index, row in enumerate(candidate_index["rows"])
    }
    candidate_train, candidate_train_flat = count_roots(
        roots["training_roots"], "candidate_index", candidate_rules
    )
    candidate_eval, candidate_eval_flat = count_roots(
        roots["evaluation_roots"], "candidate_index", candidate_rules
    )

    reference_plan_path = ROOT / lineage["task2625_reference_plan"]
    reference_plan_raw = reference_plan_path.read_bytes()
    if sha(reference_plan_raw) != lineage["task2625_reference_plan_sha256"]:
        raise ValueError("task2625 reference-plan pin mismatch")
    reference_plan = json.loads(reference_plan_raw)
    ref_pins = reference_plan["source_pins"]
    reference_pool_rel = "results/dev_aux/task2624/root-pools-v2.json"
    reference_pool_raw = (ROOT / reference_pool_rel).read_bytes()
    if sha(reference_pool_raw) != ref_pins[reference_pool_rel]:
        raise ValueError("task2625 reference-pool pin mismatch")
    reference_pool = json.loads(reference_pool_raw)
    reference_rules = {
        rule: load_compiled(
            ROOT / f"results/dev_aux/task2525/rules-{rule}.json",
            ref_pins[f"results/dev_aux/task2525/rules-{rule}.json"],
        )
        for rule in (271001, 271002, 271003, 271004)
    }
    reference_train, reference_train_flat = count_roots(
        reference_pool["training_roots"], "rule", reference_rules
    )
    reference_eval, reference_eval_flat = count_roots(
        reference_pool["evaluation_roots"], "rule", reference_rules
    )
    result = {
        "status": "PASS_FROZEN_ROOT_LEGAL_BRANCHING_CENSUS_NO_SEARCH",
        "sources": {
            "task2636_plan_sha256": sha(plan_raw),
            "task2636_candidate_index_sha256": sha(candidate_raw),
            "task2636_root_pool_sha256": sha(root_pool_raw),
            "task2625_reference_plan_sha256": sha(reference_plan_raw),
            "task2625_reference_pool_sha256": sha(reference_pool_raw),
        },
        "task2636": {
            "training_by_candidate_index": candidate_train,
            "evaluation_by_candidate_index": candidate_eval,
            "training_all": summarize(candidate_train_flat),
            "evaluation_all": summarize(candidate_eval_flat),
        },
        "task2625_reference": {
            "training_by_rule": reference_train,
            "evaluation_by_rule": reference_eval,
            "training_all": summarize(reference_train_flat),
            "evaluation_all": summarize(reference_eval_flat),
        },
        "elapsed_seconds": time.perf_counter() - began,
        "interpretation_limit": (
            "Counts only legal actions at frozen roots; no search nodes, descendant branching, "
            "training, evaluation, outcome reads, or run-time guarantee."
        ),
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()

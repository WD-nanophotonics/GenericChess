"""Compare legal root branching to the exact frozen runtime-estimate roots."""
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
OUTPUT = TASK / "cost-basis-root-branching-audit.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def summary(values: list[int]) -> dict[str, float | int]:
    ordered = sorted(values)
    return {
        "roots": len(ordered),
        "min": ordered[0],
        "p50": statistics.median(ordered),
        "mean": statistics.fmean(ordered),
        "p90_nearest_rank": ordered[math.ceil(0.90 * len(ordered)) - 1],
        "max": ordered[-1],
    }


def compile_rule(path: Path, expected_sha: str):
    raw = path.read_bytes()
    if sha(raw) != expected_sha:
        raise ValueError(f"rule hash mismatch: {path.relative_to(ROOT)}")
    return compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))


def census(rows: list[tuple[str, int, dict]], compiled: dict[str, object]):
    grouped: dict[str, list[int]] = defaultdict(list)
    for group, _family, record in rows:
        session = GameSession.replay(
            compiled[group],
            deserialize_game_record(json.dumps(record, separators=(",", ":"))),
        )
        if session.to_record().ruleset_fingerprint != record["ruleset_fingerprint"]:
            raise ValueError("full-history ruleset fingerprint mismatch")
        count = len(session.legal_actions())
        if count <= 0:
            raise ValueError("census root has no legal action")
        grouped[group].append(count)
    flat = [value for values in grouped.values() for value in values]
    return {key: summary(values) for key, values in sorted(grouped.items())}, summary(flat)


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once output already exists: {OUTPUT}")
    began = time.perf_counter()
    plan_raw = (TASK / "one-init-study-plan.json").read_bytes()
    plan = json.loads(plan_raw)
    lineage = plan["source_lineage"]
    index_raw = (ROOT / lineage["candidate_index"]).read_bytes()
    pool_raw = (ROOT / lineage["root_pool"]).read_bytes()
    if sha(index_raw) != lineage["candidate_index_sha256"] or sha(pool_raw) != lineage["root_pool_sha256"]:
        raise ValueError("task2636 candidate index or root pool hash mismatch")
    index, pool = json.loads(index_raw), json.loads(pool_raw)
    candidate_compiled = {
        str(i): compile_rule(ROOT / row["source_file"], row["ruleset_sha256"])
        for i, row in enumerate(index["rows"])
    }
    cand_train_rows = [(str(r["candidate_index"]), r["family"], r["record"]) for r in pool["training_roots"]]
    cand_eval_rows = [(str(r["candidate_index"]), r["family"], r["record"]) for r in pool["evaluation_roots"]]
    cand_train_groups, cand_train = census(cand_train_rows, candidate_compiled)
    cand_eval_groups, cand_eval = census(cand_eval_rows, candidate_compiled)

    ref_plan_raw = (ROOT / lineage["task2625_reference_plan"]).read_bytes()
    if sha(ref_plan_raw) != lineage["task2625_reference_plan_sha256"]:
        raise ValueError("task2625 reference-plan hash mismatch")
    ref_pins = json.loads(ref_plan_raw)["source_pins"]
    old_compiled = {
        str(rule): compile_rule(
            ROOT / f"results/dev_aux/task2525/rules-{rule}.json",
            ref_pins[f"results/dev_aux/task2525/rules-{rule}.json"],
        )
        for rule in (271001, 271002, 271003, 271004)
    }

    train_registration_raw = (ROOT / "results/dev_aux/task2621/cost-scan/registration.json").read_bytes()
    train_registration = json.loads(train_registration_raw)
    train_manifest_raw = (ROOT / "results/dev_aux/task2621/active-feature-probe/root-manifest.json").read_bytes()
    if sha(train_manifest_raw) != train_registration["root_manifest_sha256"]:
        raise ValueError("task2621 cost-scan root-manifest hash mismatch")
    train_manifest = json.loads(train_manifest_raw)
    train_basis_rows = [(str(r["rule"]), r["family"], r["record"]) for r in train_manifest["roots"]]
    train_basis_groups, train_basis = census(train_basis_rows, old_compiled)

    eval_plan_raw = (ROOT / "results/dev_aux/task2609/eval-plan.json").read_bytes()
    eval_registration_raw = (ROOT / "results/dev_aux/task2609/registration.json").read_bytes()
    eval_manifest_raw = (ROOT / "results/dev_aux/task2609/root-manifest.json").read_bytes()
    eval_plan, eval_registration = json.loads(eval_plan_raw), json.loads(eval_registration_raw)
    expected_manifest_sha = eval_plan["root_manifest_sha256"]
    if sha(eval_manifest_raw) != expected_manifest_sha or expected_manifest_sha != eval_registration["root_manifest_sha256"]:
        raise ValueError("task2609 evaluation root-manifest hash mismatch")
    eval_manifest = json.loads(eval_manifest_raw)
    eval_basis_rows = []
    for composite, record in eval_manifest["roots"].items():
        rule, family = composite.split(":", 1)
        eval_basis_rows.append((rule, int(family), record))
    eval_basis_groups, eval_basis = census(eval_basis_rows, old_compiled)

    result = {
        "status": "PASS_ESTIMATE_BASIS_ROOT_CENSUS_NO_SEARCH",
        "cost_estimate_basis": {
            "training": "task2621 four-rule, 80k-node-per-arm cost scan; cycle two already exposed roots per rule",
            "evaluation": "task2609 frozen evaluation root manifest; 1,536-slot run",
        },
        "pins": {
            "task2636_plan_sha256": sha(plan_raw),
            "task2636_index_sha256": sha(index_raw),
            "task2636_pool_sha256": sha(pool_raw),
            "task2625_reference_plan_sha256": sha(ref_plan_raw),
            "task2621_cost_registration_sha256": sha(train_registration_raw),
            "task2621_training_root_manifest_sha256": sha(train_manifest_raw),
            "task2609_eval_plan_sha256": sha(eval_plan_raw),
            "task2609_eval_registration_sha256": sha(eval_registration_raw),
            "task2609_evaluation_root_manifest_sha256": sha(eval_manifest_raw),
        },
        "task2636_frozen_roots": {
            "training_by_candidate": cand_train_groups,
            "evaluation_by_candidate": cand_eval_groups,
            "training_all": cand_train,
            "evaluation_all": cand_eval,
        },
        "training_cost_basis_task2621": {"by_rule": train_basis_groups, "all": train_basis},
        "evaluation_cost_basis_task2609": {"by_rule": eval_basis_groups, "all": eval_basis},
        "elapsed_seconds": time.perf_counter() - began,
        "interpretation_limit": (
            "Legal actions at fixed roots only. No search, node throughput, outcome reads, "
            "training, evaluation, or linear runtime extrapolation."
        ),
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()

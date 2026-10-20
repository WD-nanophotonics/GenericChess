"""Outcome-blind audit of task2618's remaining Chess roots and fresh seeds.

This is preparation only. It does not read games/results, run search, register a
learner comparison, or authorize training/evaluation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import chess

from results.dev_aux.task2565.train import restore


ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2618"
ROOTS = ROOT / "results/dev_aux/task2619"
COST_PLAN = TASK / "wdl-shared-cost/plan.json"
COST_RESULT = TASK / "wdl-shared-cost/result.json"
OUT = TASK / "learning-input-audit-v2.json"
SEED_NAMESPACE = "DEV_AUX_TASK2618_CHESS_TREESTRAP_V1_SEED_{}"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def derive_seeds() -> list[int]:
    return [
        int.from_bytes(hashlib.sha256(SEED_NAMESPACE.format(i).encode()).digest()[:4], "big")
        & 0x7FFFFFFF
        for i in range(4)
    ]


def plan_seed_values(value: object) -> set[int]:
    found: set[int] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"seed", "seeds", "training_seed", "ordering_seed"}:
                if isinstance(child, int) and not isinstance(child, bool):
                    found.add(child)
                elif isinstance(child, list):
                    found.update(x for x in child if isinstance(x, int) and not isinstance(x, bool))
            found.update(plan_seed_values(child))
    elif isinstance(value, list):
        for child in value:
            found.update(plan_seed_values(child))
    return found


def seed_source_plans() -> list[tuple[Path, dict]]:
    """Return independent source plans, excluding this comparison's own descendants.

    The prospective seed schedule is intentionally reused across v1/v2/v3 to
    pair learner initializations. Including one of those descendant plans in
    the schedule's own freshness audit would create a false self-collision.
    """
    plans = []
    for path in sorted((ROOT / "results/dev_aux").rglob("plan.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and value.get("task") == "DEV_AUX2618_CHESS_LEARNER_COMPARISON":
            continue
        plans.append((path, value))
    return plans


def audit() -> dict:
    if OUT.exists():
        raise FileExistsError(f"write-once audit already exists: {OUT}")
    train_path = ROOTS / "prospective-training-roots.json"
    eval_path = ROOTS / "prospective-evaluation-roots.json"
    root_audit_path = ROOTS / "root-feasibility.json"
    train_raw, eval_raw = train_path.read_bytes(), eval_path.read_bytes()
    train = json.loads(train_raw)["roots"]
    evaluation = json.loads(eval_raw)["roots"]
    root_audit = json.loads(root_audit_path.read_text(encoding="utf-8"))
    cost_plan = json.loads(COST_PLAN.read_text(encoding="utf-8"))
    cost_result = json.loads(COST_RESULT.read_text(encoding="utf-8"))

    if root_audit["status"] != "OUTCOME_BLIND_ROOT_FEASIBILITY_ONLY":
        raise ValueError("task2619 root artifact is not the expected outcome-blind audit")
    if root_audit["prospective_training"]["selected"] != 512 or len(train) != 512:
        raise ValueError("expected exactly 512 prospective training roots")
    if root_audit["prospective_evaluation"]["selected"] != 32 or len(evaluation) != 32:
        raise ValueError("expected exactly 32 prospective evaluation roots")
    if cost_plan["status"] != "FROZEN_BEFORE_SEARCH" or cost_result["status"] != "COMPLETE_COST_ONLY":
        raise ValueError("the bounded cost-only panel is not complete and auditable")

    cost_indices = cost_plan["root_indices"]
    if cost_indices != list(range(32)):
        raise ValueError("unexpected root range in the completed cost-only scan")
    cost_families = cost_plan["families"]
    if cost_families != [row["family"] for row in train[:32]]:
        raise ValueError("cost-only panel roots do not match the first 32 training roots")

    # Exclude the first 32 roots because actual terminal outcomes influenced the
    # in-memory WDL proposal trajectory even though labels were not persisted.
    selected_train = train[32:]
    if len(selected_train) != 480:
        raise ValueError("expected 480 unexposed training roots after cost-panel exclusion")
    if len(selected_train) % 4:
        raise ValueError("remaining roots must split evenly across four frozen seeds")

    def validate_rows(rows: list[dict], label: str) -> set[bytes]:
        keys: set[bytes] = set()
        for i, row in enumerate(rows):
            record = row["record"]
            raw_key = canonical(record)
            if len(record.get("moves", [])) != 8 or row.get("record_sha256") != sha(raw_key):
                raise ValueError(f"{label} root {i} has invalid full-history/hash evidence")
            restored = restore(0, None, record)
            if restored.record() != record or restored.terminal() is not None:
                raise ValueError(f"{label} root {i} fails exact ChessEnv replay")
            if raw_key in keys:
                raise ValueError(f"duplicate exact root in {label} pool")
            keys.add(raw_key)
        return keys

    train_keys = validate_rows(selected_train, "selected training")
    eval_keys = validate_rows(evaluation, "evaluation")
    cost_keys = validate_rows(train[:32], "cost-only")
    if train_keys & eval_keys or cost_keys & train_keys or cost_keys & eval_keys:
        raise ValueError("exact-history overlap among selected pools")

    source_seed_values: set[int] = set()
    seed_source_count = 0
    for path, value in seed_source_plans():
        source_seed_values.update(plan_seed_values(value))
        seed_source_count += 1
    seeds = derive_seeds()
    if len(set(seeds)) != 4 or any(seed in source_seed_values for seed in seeds):
        raise ValueError("derived training seed collides with a recorded seed")

    train_root_digest = sha(b"\n".join(canonical(row["record"]) for row in selected_train))
    eval_root_digest = sha(b"\n".join(canonical(row["record"]) for row in evaluation))
    result = {
        "status": "PREPARATION_AUDIT_ONLY_NOT_REGISTERED",
        "task": "DEV_AUX2618_CHESS_LEARNER_COMPARISON_INPUTS",
        "question": "Can the preselected remaining Chess roots and deterministic fresh seeds support a paired TreeStrap/TDLeaf/WDL comparison without reusing the cost-only outcomes?",
        "sources": {
            "task2619_training_roots": {"path": train_path.relative_to(ROOT).as_posix(), "sha256": sha(train_raw)},
            "task2619_evaluation_roots": {"path": eval_path.relative_to(ROOT).as_posix(), "sha256": sha(eval_raw)},
            "task2619_root_audit": {"path": root_audit_path.relative_to(ROOT).as_posix(), "sha256": sha(root_audit_path.read_bytes())},
            "task2618_cost_plan": {"path": COST_PLAN.relative_to(ROOT).as_posix(), "sha256": sha(COST_PLAN.read_bytes())},
            "task2618_cost_result": {"path": COST_RESULT.relative_to(ROOT).as_posix(), "sha256": sha(COST_RESULT.read_bytes())},
        },
        "selection": {
            "cost_only_training_root_indices_excluded": cost_indices,
            "cost_only_training_families_excluded": cost_families,
            "training_root_indices_remaining": [32, 512],
            "training_root_count_remaining": len(selected_train),
            "training_roots_per_seed_if_four_seed_design": len(selected_train) // 4,
            "training_root_records_sha256": train_root_digest,
            "training_family_range": [selected_train[0]["family"], selected_train[-1]["family"]],
            "evaluation_family_ids": [row["family"] for row in evaluation],
            "evaluation_root_count": len(evaluation),
            "evaluation_root_records_sha256": eval_root_digest,
            "exact_history_overlap_training_evaluation": 0,
        },
        "seed_schedule": {
            "namespace": SEED_NAMESPACE,
            "seeds": seeds,
            "derivation": "first four SHA-256 bytes interpreted unsigned big-endian, masked to 31 bits; no outcome inputs",
            "historical_plan_files_scanned": seed_source_count,
            "collision_with_recorded_plan_seeds": False,
        },
        "claims_limited_to": root_audit["claim_limit"],
        "search_or_outcome_access": False,
        "registration_or_launch_authorized": False,
        "python_chess_version": chess.__version__,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))

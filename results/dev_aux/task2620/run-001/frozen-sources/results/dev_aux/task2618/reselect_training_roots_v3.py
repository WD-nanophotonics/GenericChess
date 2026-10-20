"""Prepare a clean v3 Chess root panel, excluding the entire v2 registered panel.

This is outcome-blind preparation only. It reads v2 root IDs and exact rule
records, not game outcomes, weights, labels or training traces.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2618"
TRAIN_PATH = ROOT / "results/dev_aux/task2619/prospective-training-roots.json"
EVAL_PATH = ROOT / "results/dev_aux/task2619/prospective-evaluation-roots.json"
AUDIT_PATH = TASK / "learning-input-audit-v2.json"
V2_PLAN_PATH = TASK / "learner-comparison-v2/plan.json"
OUTPUT_DIR = TASK / "learner-comparison-v3-prep"
PANEL_SIZE = 120
SEED_NAMESPACE = "DEV_AUX_TASK2618_CHESS_TRAINING_ROOT_PANEL_V3"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def panel_seed() -> int:
    return int.from_bytes(hashlib.sha256(SEED_NAMESPACE.encode()).digest()[:4], "big")


def build_panel(training_doc: dict, evaluation_doc: dict, audit: dict,
                v2_plan: dict, source_hashes: dict[str, str]) -> dict:
    selection = audit["selection"]
    train_start, train_end = selection["training_root_indices_remaining"]
    candidates = training_doc["roots"][train_start:train_end]
    expected_count = selection.get("training_root_count_remaining", train_end - train_start)
    if len(candidates) != expected_count or len({row["family"] for row in candidates}) != expected_count:
        raise ValueError("eligible training pool differs from the audited exact root set")
    excluded = set(v2_plan.get("training_families", []))
    known = {row["family"] for row in candidates}
    if len(excluded) != PANEL_SIZE or not excluded <= known:
        raise ValueError("v2 registered panel differs from the expected 120 audited families")
    available = [row for row in candidates if row["family"] not in excluded]
    if len(available) < PANEL_SIZE:
        raise ValueError("not enough roots remain after excluding the full v2 panel")
    ordered = sorted(available, key=lambda row: row["family"])
    random.Random(panel_seed()).shuffle(ordered)
    selected = ordered[:PANEL_SIZE]
    selected_keys = {canonical(row["record"]) for row in selected}
    eval_keys = {canonical(row["record"]) for row in evaluation_doc["roots"]}
    if selected_keys & eval_keys:
        raise ValueError("v3 training panel overlaps the frozen evaluation panel")
    return {
        "status": "PREPARATION_ONLY_NOT_REGISTERED",
        "task": "DEV_AUX2618_CHESS_LEARNER_COMPARISON_V3_ROOT_PANEL",
        "selection_method": "Sort eligible audited roots by family, exclude every family in the registered v2 training panel, shuffle with the fixed v3 seed namespace, and take the first 120; share the new panel across all learner seeds and methods.",
        "selection_seed_namespace": SEED_NAMESPACE,
        "selection_seed": panel_seed(),
        "panel_size": PANEL_SIZE,
        "source_training_range": [train_start, train_end],
        "registered_v2_panel_families_excluded": sorted(excluded),
        "eligible_remaining_count": len(available),
        "evaluation_root_count": len(evaluation_doc["roots"]),
        "training_evaluation_exact_record_overlap": 0,
        "selected_exact_record_set_sha256": sha(b"\n".join(
            canonical(row["record"]) for row in selected
        )),
        "sources": source_hashes,
        "selection_field_projection": ["family", "record"],
        "search_started": False,
        "outcome_fields_used_for_selection": False,
        "roots": selected,
    }


def prepare() -> dict:
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"write-once v3 root-panel output already exists: {OUTPUT_DIR}")
    training_doc = json.loads(TRAIN_PATH.read_text(encoding="utf-8"))
    evaluation_doc = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    v2_plan = json.loads(V2_PLAN_PATH.read_text(encoding="utf-8"))
    panel = build_panel(
        training_doc, evaluation_doc, audit, v2_plan,
        source_hashes={
            "training_roots_sha256": sha(TRAIN_PATH.read_bytes()),
            "evaluation_roots_sha256": sha(EVAL_PATH.read_bytes()),
            "input_audit_sha256": sha(AUDIT_PATH.read_bytes()),
            "v2_registered_plan_sha256": sha(V2_PLAN_PATH.read_bytes()),
            "root_selector_source_sha256": sha(Path(__file__).read_bytes()),
        },
    )
    OUTPUT_DIR.mkdir()
    raw = (json.dumps(panel, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    with (OUTPUT_DIR / "root-selection.json").open("xb") as stream:
        stream.write(raw)
        stream.flush()
    return {
        "status": panel["status"],
        "root_selection_sha256": sha(raw),
        "panel_size": panel["panel_size"],
        "excluded_v2_registered_roots": len(panel["registered_v2_panel_families_excluded"]),
        "eligible_remaining_roots": panel["eligible_remaining_count"],
        "evaluation_overlap": panel["training_evaluation_exact_record_overlap"],
        "search_started": panel["search_started"],
    }


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))

"""Prepare a fresh v4 Chess root panel excluding all v1/v2/v3 exposure.

Selection uses an outcome-free v1 family/unstarted projection, registered
family lists from v2/v3 plans, and exact training/evaluation root records. It
never uses game outcomes, weights, learner traces, or search results.
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
V1_EXPOSURE_PATH = TASK / "learner-comparison-v4-prep/v1-exposure-projection.json"
V2_PLAN_PATH = TASK / "learner-comparison-v2/plan.json"
V3_PLAN_PATH = TASK / "learner-comparison-v3/plan.json"
OUTPUT_DIR = TASK / "learner-comparison-v4-prep-verified"
PANEL_SIZE = 120
V1_EXPOSED_COUNT = 51
REGISTERED_PANEL_SIZE = 120
V1_V2_OVERLAP = 0
V1_V3_OVERLAP = 18
V2_V3_OVERLAP = 0
ELIGIBLE_COUNT = 207
SEED_NAMESPACE = "DEV_AUX_TASK2618_CHESS_TRAINING_ROOT_PANEL_V4"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def panel_seed() -> int:
    return int.from_bytes(hashlib.sha256(SEED_NAMESPACE.encode()).digest()[:4], "big")


def started_family_ids(projection: dict) -> set[int]:
    if (projection.get("status") != "OUTCOME_FREE_EXPOSURE_PROJECTION"
            or projection.get("outcome_fields_used") is not False
            or projection.get("projected_fields") != ["family", "unstarted"]):
        raise ValueError("v1 exposure input is not the expected outcome-free projection")
    exposed: set[int] = set()
    for row in projection.get("rows", []):
        # Project only the fields that determine exposure; ignore all outcomes.
        family = row.get("family")
        if row.get("unstarted") is not True:
            if not isinstance(family, int):
                raise ValueError("started v1 row has no integer family id")
            exposed.add(family)
    if len(exposed) != V1_EXPOSED_COUNT:
        raise ValueError("v1 exposure family count differs from the audited 51")
    return exposed


def build_panel(training_doc: dict, evaluation_doc: dict, audit: dict,
                exposure_projection: dict, v2_plan: dict, v3_plan: dict,
                source_hashes: dict[str, str]) -> dict:
    selection = audit["selection"]
    train_start, train_end = selection["training_root_indices_remaining"]
    candidates = training_doc["roots"][train_start:train_end]
    expected_count = selection.get("training_root_count_remaining", train_end - train_start)
    known = {row["family"] for row in candidates}
    if len(candidates) != expected_count or len(known) != expected_count:
        raise ValueError("eligible training pool differs from the audited exact root set")

    v1_exposed = started_family_ids(exposure_projection)
    v2_registered = set(v2_plan.get("training_families", []))
    v3_registered = set(v3_plan.get("training_families", []))
    if len(v2_registered) != REGISTERED_PANEL_SIZE or len(v3_registered) != REGISTERED_PANEL_SIZE:
        raise ValueError("v2/v3 registered panels must each contain 120 unique families")
    if not (v1_exposed | v2_registered | v3_registered) <= known:
        raise ValueError("an exposed/registered family falls outside the audited pool")
    overlaps = {
        "v1_v2": len(v1_exposed & v2_registered),
        "v1_v3": len(v1_exposed & v3_registered),
        "v2_v3": len(v2_registered & v3_registered),
    }
    expected_overlaps = {"v1_v2": V1_V2_OVERLAP, "v1_v3": V1_V3_OVERLAP,
                         "v2_v3": V2_V3_OVERLAP}
    if overlaps != expected_overlaps:
        raise ValueError("registered-panel overlap differs from the audited v1/v2/v3 union")
    excluded = v1_exposed | v2_registered | v3_registered
    available = [row for row in candidates if row["family"] not in excluded]
    if len(available) != ELIGIBLE_COUNT:
        raise ValueError("eligible root count differs from the audited 207-family union")
    ordered = sorted(available, key=lambda row: row["family"])
    random.Random(panel_seed()).shuffle(ordered)
    selected = ordered[:PANEL_SIZE]
    selected_keys = {canonical(row["record"]) for row in selected}
    eval_keys = {canonical(row["record"]) for row in evaluation_doc["roots"]}
    if selected_keys & eval_keys:
        raise ValueError("v4 training panel overlaps the frozen evaluation panel")
    return {
        "status": "PREPARATION_ONLY_NOT_REGISTERED",
        "task": "DEV_AUX2618_CHESS_LEARNER_COMPARISON_V4_ROOT_PANEL",
        "selection_method": "Exclude v1 started families and the complete registered v2/v3 family panels; sort remaining audited roots by family, shuffle with the fixed v4 seed namespace, and take the first 120 paired roots.",
        "selection_seed_namespace": SEED_NAMESPACE,
        "selection_seed": panel_seed(),
        "panel_size": PANEL_SIZE,
        "source_training_range": [train_start, train_end],
        "v1_started_families_excluded": sorted(v1_exposed),
        "v2_registered_families_excluded": sorted(v2_registered),
        "v3_registered_families_excluded": sorted(v3_registered),
        "registered_panel_pairwise_overlap_counts": overlaps,
        "excluded_union_count": len(excluded),
        "eligible_remaining_count": len(available),
        "evaluation_root_count": len(evaluation_doc["roots"]),
        "training_evaluation_exact_record_overlap": 0,
        "selected_exact_record_set_sha256": sha(b"\n".join(
            canonical(row["record"]) for row in selected
        )),
        "sources": source_hashes,
        "selection_field_projection": ["family", "record", "unstarted"],
        "search_started": False,
        "outcome_fields_used_for_selection": False,
        "roots": selected,
    }


def prepare() -> dict:
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"write-once v4 root-panel output already exists: {OUTPUT_DIR}")
    training_doc = json.loads(TRAIN_PATH.read_text(encoding="utf-8"))
    evaluation_doc = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    exposure_raw = V1_EXPOSURE_PATH.read_bytes()
    exposure_projection = json.loads(exposure_raw)
    v2_plan = json.loads(V2_PLAN_PATH.read_text(encoding="utf-8"))
    v3_plan = json.loads(V3_PLAN_PATH.read_text(encoding="utf-8"))
    panel = build_panel(
        training_doc, evaluation_doc, audit, exposure_projection, v2_plan, v3_plan,
        source_hashes={
            "training_roots_sha256": sha(TRAIN_PATH.read_bytes()),
            "evaluation_roots_sha256": sha(EVAL_PATH.read_bytes()),
            "input_audit_sha256": sha(AUDIT_PATH.read_bytes()),
            "v1_exposure_projection_file_sha256": sha(exposure_raw),
            "v1_exposure_source_sha256": exposure_projection["source_sha256"],
            "v2_registered_plan_sha256": sha(V2_PLAN_PATH.read_bytes()),
            "v3_registered_plan_sha256": sha(V3_PLAN_PATH.read_bytes()),
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
        "excluded_union_count": panel["excluded_union_count"],
        "eligible_remaining_count": panel["eligible_remaining_count"],
        "evaluation_overlap": panel["training_evaluation_exact_record_overlap"],
        "search_started": panel["search_started"],
    }


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))

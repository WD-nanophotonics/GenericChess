"""Durable contracts for the F23Q V10 corpus and horizon overlay."""

from __future__ import annotations

import hashlib
import json
from collections import Counter

from scripts import build_f23q_preference_corpus_r8 as f23q


ROOT = f23q.ROOT
FIXTURES = ROOT / "tests" / "fixtures"
PLAN = FIXTURES / "f23q_candidate_plan_r8.json"
V9 = FIXTURES / "evaluator_v2_corpus_v9.json"
V10 = FIXTURES / "evaluator_v2_corpus_v10.json"
DIAGNOSIS = FIXTURES / "f23q_v9_diagnosis.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_r8_plan_and_v9_diagnosis_are_frozen():
    plan = load(PLAN)
    diagnosis = load(DIAGNOSIS)
    assert plan["candidate_plan_sha256"] == f23q.plan_digest(plan)
    assert plan["candidate_count"] == 32
    assert diagnosis["source_fixture_sha256"] == hashlib.sha256(V9.read_bytes()).hexdigest()
    assert diagnosis["eligible_development"] == 22
    assert diagnosis["eligible_holdout"] == 5
    assert diagnosis["capture_development_count"] == 9
    assert diagnosis["additional_non_capture_development_required_for_35_percent"] == 4
    assert diagnosis["holdout_deficit_to_six"] == 1
    assert diagnosis["development_by_horizon_class"] == {
        "HORIZON_SENSITIVITY_UNKNOWN": 16,
        "HORIZON_STABLE_EXACT": 1,
        "MATERIALLY_MAX_PLY_DEPENDENT": 5,
    }


def test_v10_preserves_history_and_carries_corrected_overlay():
    v9 = load(V9)
    v10 = load(V10)
    assert v10["source_v9_fixture_sha256"] == hashlib.sha256(V9.read_bytes()).hexdigest()
    assert v10["candidate_plan_sha256"] == load(PLAN)["candidate_plan_sha256"]
    assert v10["historical_horizon_recertification"]
    assert set(v9["observed_cross_split_behavioral_collision_ids"]).issubset(
        set(v10["observed_cross_split_behavioral_collision_ids"])
    )
    assert v10["residual_eligible_behavioral_leakage_ids"] == []
    assert v10["residual_eligible_source_lineage_leakage_ids"] == []
    assert v10["production_changed"] is False
    assert v10["reference_independence"] == {
        "external_reference_opened": False,
        "evaluator_inspection": False,
        "forbidden_inputs_consulted": False,
    }


def test_r8_lineages_are_derived_from_canonical_keys_and_split_without_targeting():
    plan = load(PLAN)
    v10 = load(V10)
    records = {row["id"]: row for row in v10["records"]}
    candidates = [candidate for family in plan["families"] for candidate in family["candidates"]]
    assert len({candidate["source_lineage_key"] for candidate in candidates}) == 32
    for candidate in candidates:
        row = records[candidate["id"]]
        assert row["source_lineage_id"] == f23q.lineage_id(candidate["source_lineage_key"])
        assert row["planned_split"] == f23q.split(row["source_lineage_id"])


def test_v10_gate_and_next_boundary_expose_horizon_blocker():
    v10 = load(V10)
    effective = v10["effective_preference_representatives"]
    development = [row for row in effective if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in effective if row["planned_split"] == "HOLDOUT"]
    assert len(development) == 32
    assert len(holdout) == 10
    assert v10["coverage"]["r8_solved"] == 32
    assert v10["coverage"]["r8_unresolved"] == 0
    assert Counter(row["horizon_dependence"] for row in effective) == Counter({
        "MATERIALLY_MAX_PLY_DEPENDENT": 15,
        "HORIZON_SENSITIVITY_UNKNOWN": 24,
        "HORIZON_STABLE_EXACT": 3,
    })
    assert v10["advancement_gate"]["items"]["non_max_ply_minimum"] is False
    assert v10["advancement_gate"]["passes"] is False
    assert v10["selected_next_boundary"] == "F23R_HORIZON_REFERENCE_CERTIFICATION_FOUNDATION"

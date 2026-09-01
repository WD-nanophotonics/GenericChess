"""Durable contracts for the corrected V9/R7 reference corpus accounting."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts import build_f23p_preference_corpus_r7 as f23p
from scripts import audit_f23p_v8_gate


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
PLAN = FIXTURES / "f23p_candidate_plan_r7.json"
V9 = FIXTURES / "evaluator_v2_corpus_v9.json"


def load():
    return json.loads(V9.read_text(encoding="utf-8"))


def test_v8_diagnosis_and_r7_plan_are_frozen():
    v9 = load()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    diagnosis = audit_f23p_v8_gate.diagnose()
    assert diagnosis["source_fixture_sha256"] == "b35d5898bb4d3b3533802311e68541b9c602c65ccd2a77251bb9b24f8ff5cda7"
    assert diagnosis["capture_development_count"] == 9
    assert diagnosis["additional_non_capture_development_required_for_35_percent"] == 3
    assert diagnosis["holdout_deficit_to_six"] == 1
    assert diagnosis["residual_eligible_behavioral_leakage_ids"] == []
    assert plan["candidate_plan_sha256"] == f23p.plan_digest(plan)
    assert v9["candidate_plan_sha256"] == plan["candidate_plan_sha256"]
    assert v9["candidate_plan"] == plan
    assert len(plan["candidate_order"]) == 24


def test_lineage_derivation_and_split_are_not_hash_targeted():
    v9 = load()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    records = v9["records"]
    for candidate in [c for family in plan["families"] for c in family["candidates"]]:
        expected = f23p.lineage_id(candidate["source_lineage_key"])
        row = next(item for item in records if item["id"] == candidate["id"])
        assert row["source_lineage_id"] == expected
        assert row["planned_split"] == f23p.split(expected)
    for lineage in {row["source_lineage_id"] for row in records}:
        assert len({row["planned_split"] for row in records if row["source_lineage_id"] == lineage}) == 1


def test_unknown_horizon_cases_do_not_count_as_stable():
    v9 = load()
    effective = v9["effective_preference_representatives"]
    unknown = [row for row in effective if row["horizon_dependence"] == "HORIZON_SENSITIVITY_UNKNOWN"]
    stable = [row for row in effective if row["horizon_dependence"] in {"NATURAL_TERMINAL_CERTIFIED", "HORIZON_STABLE_EXACT"}]
    assert len(unknown) == 16
    assert len(stable) == v9["coverage"]["stable_horizon_development"] + len([row for row in effective if row["planned_split"] == "HOLDOUT" and row["horizon_dependence"] in {"NATURAL_TERMINAL_CERTIFIED", "HORIZON_STABLE_EXACT"}])
    assert v9["advancement_gate"]["items"]["non_max_ply_minimum"] is False


def test_observed_collision_is_retained_but_residual_leakage_is_zero():
    v9 = load()
    assert len(v9["observed_cross_split_behavioral_collision_ids"]) == 3
    assert v9["residual_eligible_behavioral_leakage_ids"] == []
    assert v9["residual_eligible_source_lineage_leakage_ids"] == []
    effective_ids = {row["decision_certificate_fingerprint"] for row in v9["effective_preference_representatives"]}
    assert not (effective_ids & set(v9["observed_cross_split_behavioral_collision_ids"]))


def test_v9_gate_and_historical_integrity_are_exposed():
    v9 = load()
    dev = [row for row in v9["effective_preference_representatives"] if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in v9["effective_preference_representatives"] if row["planned_split"] == "HOLDOUT"]
    assert len(dev) == 22
    assert len(holdout) == 5
    assert len(Counter(row["construction_family"] for row in dev)) == 5
    assert v9["advancement_gate"]["passes"] is False
    assert v9["selected_next_boundary"] == "F23Q_REFERENCE_PREFERENCE_CORPUS_R8"
    assert hashlib.sha256((FIXTURES / "evaluator_v2_corpus_v8.json").read_bytes()).hexdigest() == "b35d5898bb4d3b3533802311e68541b9c602c65ccd2a77251bb9b24f8ff5cda7"
    assert hashlib.sha256((FIXTURES / "f23o_candidate_plan_r6.json").read_bytes()).hexdigest() == "8b026fc1ab32a2a50ab6c049459982fc308c4c63e38957377d42edfe6c64ca99"

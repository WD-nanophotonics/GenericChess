"""F23J independent-mechanic corpus and exact-solver refusal contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_f23j_preference_corpus_r4 as f23j


ROOT = Path(__file__).parents[1]
V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
V4 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json"
V5 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v5.json"
F23F = ROOT / "tests" / "fixtures" / "evaluator_v2_candidate_spec_f23f.json"
V6 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v6.json"


def test_f23j_rebuild_is_deterministic_and_history_is_byte_immutable():
    frozen = {path: path.read_bytes() for path in (V1, V2, V3, V4, V5, F23F)}
    expected = json.loads(V6.read_text(encoding="utf-8"))
    assert f23j.build_corpus() == expected
    assert {path: path.read_bytes() for path in frozen} == frozen
    assert expected["historical_strata"]["v4_sha256"] == hashlib.sha256(frozen[V4]).hexdigest()
    assert expected["historical_strata"]["v5_sha256"] == hashlib.sha256(frozen[V5]).hexdigest()


def test_f23j_plan_is_frozen_and_attempts_independent_mechanics_without_fit_inspection():
    fixture = json.loads(V6.read_text(encoding="utf-8"))
    plan = fixture["candidate_plan"]
    assert fixture["source_f23j_plan_sha256"] == f23j._plan_digest()
    assert fixture["coverage"]["planned_candidate_count"] == 36
    assert fixture["coverage"]["construction_family_attempt_count"] == 6
    assert fixture["coverage"]["mechanic_family_attempt_count"] == 6
    assert {item["construction_family"] for item in plan} >= {
        "ordinary_anchor_movement",
        "capture_recapture_tactics",
        "drop_hand_tactics",
        "promotion_race",
        "semantic_guard_auxiliary",
        "auxiliary_reply_chain_control",
    }
    source = (ROOT / "scripts" / "build_f23j_preference_corpus_r4.py").read_text(encoding="utf-8")
    assert "audit_f23i_evaluator_v2_prototype_r3" not in source
    assert "ADR-040" not in source
    assert "Evaluator" not in source
    assert "AlphaSho" not in source


def test_f23j_unresolved_candidates_are_refused_and_no_fake_gate_is_reported():
    fixture = json.loads(V6.read_text(encoding="utf-8"))
    coverage = fixture["coverage"]
    effective = fixture["effective_orbits"]
    assert coverage["physical_solved_count"] == 6
    assert coverage["canonical_solved_count"] == 2
    assert coverage["unresolved_candidate_count"] == 30
    assert coverage["effective_development_count"] == 1
    assert coverage["effective_holdout_count"] == 0
    assert fixture["advancement_gate"]["passes"] is False
    assert fixture["decision"]["selected_next_boundary"] == "F23K_EXACT_REFERENCE_SOLVER_FOUNDATION"
    assert effective["fit_eligible_development_orbit_ids"]
    assert effective["validation_eligible_holdout_orbit_ids"] == []
    assert all(row["strong"] for row in fixture["generic_exact"])
    assert all(row["preference_authority"]["proof_depth_class"] == "MULTIPLY_DEPENDENT" for row in fixture["generic_exact"])


def test_f23j_deliberate_sibling_source_is_excluded_from_validation_accounting():
    fixture = json.loads(V6.read_text(encoding="utf-8"))
    control = next(item for item in fixture["candidate_plan"] if item["builder"] == "f23g_reply_chain_control")
    assert control["source_families"][0] == control["source_families"][2]
    assert control["splits"][0] == "DEVELOPMENT"
    assert control["splits"][2] == "HOLDOUT"
    assert control["source_families"][0] in fixture["effective_orbits"]["excluded_source_family_leakage_ids"]
    assert fixture["effective_orbits"]["validation_eligible_holdout_orbit_ids"] == []

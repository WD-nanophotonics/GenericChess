"""Permanent F23T/R10 runner, enumeration, witness, and V12 gate contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_f23t_natural_terminal_corpus_r10 as builder


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
V10 = FIXTURES / "evaluator_v2_corpus_v10.json"
V11 = FIXTURES / "evaluator_v2_corpus_v11.json"
DIAGNOSIS = FIXTURES / "f23s_r9_failure_diagnosis.json"
PLAN = FIXTURES / "f23t_candidate_plan_r10.json"
V12 = FIXTURES / "evaluator_v2_corpus_v12.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_r9_diagnosis_records_historical_runner_and_strict_witness_gap():
    diagnosis = load(DIAGNOSIS)
    assert diagnosis["r9_runner_contract_mismatch"] == {
        "abstraction_ladder_executed": False,
        "historical_note": "R9 declared both contracts but used direct V3 calls and one max_nodes=100000 abstraction call.",
        "v3_isolated_8_second_wall": False,
    }
    assert diagnosis["strict_reaudit"]["f23s-r9-semantic-02"] == {"passes": False, "reason": "CUSTOM_SEMANTIC_PATTERN_REQUIRED"}
    assert set(diagnosis["by_family"]) == {
        "ordinary_anchor_terminal", "capture_recapture_terminal", "drop_hand_terminal",
        "promotion_terminal", "semantic_guard_terminal", "interposition_leaper_terminal",
    }


def test_r10_plan_uses_structural_descriptor_lineage_without_display_id():
    plan = load(PLAN)
    body = dict(plan)
    digest = body.pop("candidate_plan_sha256")
    assert hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == digest
    assert plan["candidate_count"] <= 144
    assert plan["candidate_count"] == sum(plan["candidate_count_per_family"].values())
    assert all(2 <= count <= 12 for count in plan["candidate_count_per_family"].values())
    for family in plan["families"]:
        for candidate in family["candidates"]:
            descriptor = builder._descriptor(family["construction_family"], family["mechanic_family"], family["builder"], candidate)
            lineage = hashlib.sha256(descriptor.encode()).hexdigest()
            assert candidate["source_lineage_key"] == descriptor
            assert candidate["source_lineage_id"] == "r10-" + lineage[:16]
            assert candidate["id"] == f"f23t-r10-{family['construction_family']}-{lineage[:10]}"
            assert candidate["planned_split"] == builder._split(candidate["source_lineage_id"])
            renamed = dict(candidate, id="display-id-does-not-enter-lineage")
            assert builder._descriptor(family["construction_family"], family["mechanic_family"], family["builder"], renamed) == descriptor


def test_v12_excludes_v10_v11_and_requires_strict_abstract_supervision():
    v10 = load(V10)
    v11 = load(V11)
    v12 = load(V12)
    historical = {row["id"] for row in v10["effective_preference_representatives"]} | {row["id"] for row in v11["eligible_preference_representatives"]}
    assert not historical.intersection(v12["fit_eligible_development_orbit_ids"])
    assert not historical.intersection(v12["validation_eligible_holdout_orbit_ids"])
    assert v12["diagnostics"] == {
        "abstraction_certified": 7,
        "abstraction_refused": 1,
        "all_equal": 11,
        "core_mechanic_effective": {"anchor_check_movement": 5, "capture_recapture": 1, "drop_hand": 0, "promotion_choice": 0},
        "observed_cross_split_orbits": 0,
        "planned": 60,
        "preference_bearing": 8,
        "residual_cross_split_orbits": 0,
        "strict_witness_qualified": 8,
        "v3_exact": 19,
        "v3_unresolved": 41,
    }
    assert all(row["abstraction_status"] == "MAX_PLY_ABSTRACT_CERTIFIED" for row in v12["eligible_preference_representatives"])
    assert all(row["strict_witness_status"] == "PASS" for row in v12["eligible_preference_representatives"])
    assert v12["coverage"]["development"] == 6
    assert v12["coverage"]["holdout"] == 1


def test_v12_full_and_signal_gates_are_explicitly_failed_and_boundary_is_reassessment():
    v12 = load(V12)
    assert v12["advancement_gate"]["passes"] is False
    assert v12["signal_probe_gate"]["passes"] is False
    assert v12["selected_next_boundary"] == "F23U_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT"
    assert v12["historical_source_hashes"]["v10"] == hashlib.sha256(V10.read_bytes()).hexdigest()
    assert v12["historical_source_hashes"]["v11"] == hashlib.sha256(V11.read_bytes()).hexdigest()
    assert v12["production_changed"] is False
    assert v12["v11_rewritten"] is False


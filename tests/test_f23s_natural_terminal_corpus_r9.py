"""Permanent contracts for the clean F23S/R9 V11 corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_f23s_natural_terminal_corpus_r9 as builder


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
PLAN = FIXTURES / "f23s_candidate_plan_r9.json"
V10 = FIXTURES / "evaluator_v2_corpus_v10.json"
R2 = FIXTURES / "f23r_v10_horizon_certification_r2.json"
V11 = FIXTURES / "evaluator_v2_corpus_v11.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_r9_plan_is_frozen_and_deterministic():
    plan = load(PLAN)
    body = dict(plan)
    digest = body.pop("candidate_plan_sha256")
    assert digest == hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    regenerated = builder.make_plan()
    assert regenerated["candidate_plan_sha256"] == digest
    assert regenerated["candidate_order"] == plan["candidate_order"]
    assert plan["candidate_count"] == 48
    assert plan["candidate_count_per_family"] == 8
    assert len(plan["families"]) == 6
    assert all(len(family["candidates"]) == 8 for family in plan["families"])
    assert len({candidate["source_lineage_id"] for family in plan["families"] for candidate in family["candidates"]}) == 48


def test_r9_split_and_source_hash_contracts():
    plan = load(PLAN)
    v11 = load(V11)
    assert v11["candidate_plan"]["candidate_plan_sha256"] == plan["candidate_plan_sha256"]
    assert plan["source_v10_sha256"] == hashlib.sha256(V10.read_bytes()).hexdigest()
    assert plan["source_f23r_r2_sha256"] == hashlib.sha256(R2.read_bytes()).hexdigest()
    for family in plan["families"]:
        for candidate in family["candidates"]:
            assert candidate["planned_split"] == builder._split(candidate["source_lineage_id"])


def test_v11_excludes_historical_v10_supervision_and_requires_abstract_certificates():
    v10 = load(V10)
    v11 = load(V11)
    historical = {row["id"] for row in v10["effective_preference_representatives"]}
    assert not historical.intersection(v11["fit_eligible_development_orbit_ids"])
    assert not historical.intersection(v11["validation_eligible_holdout_orbit_ids"])
    assert set(v11["v10_historical_control_ids"]) == historical
    assert all(row["abstraction_status"] == "MAX_PLY_ABSTRACT_CERTIFIED" for row in v11["eligible_preference_representatives"])
    assert all(row["v3_exact"] and row["preference_bearing"] and row["mechanic_witness"] for row in v11["eligible_preference_representatives"])
    assert v11["coverage"]["development"] == 1
    assert v11["coverage"]["holdout"] == 0
    assert v11["diagnostics"] == {
        "abstraction_certified": 1,
        "abstraction_refused": 18,
        "all_equal": 20,
        "duplicate_orbit_groups": 0,
        "observed_leakage_groups": 0,
        "preference_bearing": 19,
        "residual_leakage_groups": 0,
        "v3_exact": 39,
        "v3_unresolved": 9,
        "witness_qualified": 23,
    }


def test_v11_gate_and_next_boundary_are_explicit():
    v11 = load(V11)
    assert v11["advancement_gate"]["passes"] is False
    assert v11["signal_probe_gate"]["passes"] is False
    assert v11["selected_next_boundary"] == "F23T_NATURAL_TERMINAL_REFERENCE_CORPUS_R10"
    assert v11["historical_source_hashes"]["v10"] == hashlib.sha256(V10.read_bytes()).hexdigest()
    assert v11["production_changed"] is False
    assert v11["v10_rewritten"] is False


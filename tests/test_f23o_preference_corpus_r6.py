"""Durable contracts for the combined V7 + frozen-plan R6 corpus."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts import build_f23o_preference_corpus_r6 as f23o
from scripts import audit_f23n_v7_family_diagnosis as diagnosis


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
PLAN = FIXTURES / "f23o_candidate_plan_r6.json"
V8 = FIXTURES / "evaluator_v2_corpus_v8.json"
HISTORICAL = {
    "evaluator_v2_corpus_v1.json": "4c88b409b9dd8188f0c9f2c587c55199b74c8b9bc3bec3a91457e0af499d73ac",
    "evaluator_v2_corpus_v2.json": "16244ab39508d319fdf9cdbbe69fb813daa4835f12a54f2a227d9794aacc11fa",
    "evaluator_v2_corpus_v3.json": "34c59315b11f6b8f18bf3746e870c1b48bf7645c1e18718b77bba7fdcd77ba97",
    "evaluator_v2_corpus_v4.json": "de6910025ab78a2bdf04fafeaedfdf2d18af8c67a3a45d042ecff0e4412e96a0",
    "evaluator_v2_corpus_v5.json": "3a94a8a295a4c0de197a45f593d44ff03da0e620cdcd56824a9bca4bcf6341c8",
    "evaluator_v2_corpus_v6.json": "6aa8c3e90b3c1ea0919ccc16ba61b070aa67bbd03902c1b5fd19746a483b59d7",
    "evaluator_v2_candidate_spec_f23f.json": "88894da595105a4e53a4d21dbab69c6565cf8417b8c8e24f424f08397e186097",
    "f23k_solver_capability_v1.json": "4b32b3e9e942d9dbd282f2c217c1115554e2789a01f70b9f5afd2bb5e126cd51",
    "f23k_solver_capability_v2.json": "2e6a11231a2148f6bb94e9ff24e0b453eb9a8e25d619c9606eb8ea97cb7c5dd7",
    "f23l_solver_capability_v3.json": "418eed0baaf1fc01673f1010d3784964025225fffd6337cdfb50d54998be50a9",
    "f23m_solver_capability_v4.json": "4bcf8a01dd86907aa1107ec432583259b09ea1dcbb552fb4d6855b9461aa9c46",
    "f23m_solver_capability_v4r1.json": "2419f2393516f6d7f4e2971483dd0e49560009e1dd0e3aa6c4b5fa8665c3088f",
    "f23m_solver_capability_v4r1_full.json": "90fbb87ede90d6a8c2416a976772cd4a36aa1307b5238f13c97a9be8b5c39b14",
}


def _load(path=V8):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v7_diagnosis_is_deterministic_and_result_only():
    report = diagnosis.diagnose()
    assert report["source_fixture_sha256"] == "57d0d40ad4e74815ca1c542c2fa680750ea8a6411e47249a3892f23954dd064b"
    assert set(report["diagnosis"]) == {
        "ordinary_anchor_movement",
        "capture_recapture_tactics",
        "drop_hand_tactics",
        "promotion_choice",
        "semantic_guard_auxiliary",
    }
    assert report["selection_guidance"]["forbidden_inputs_consulted"] is False
    assert report["diagnosis"]["promotion_choice"]["all_equal_count"] == 8
    assert report["diagnosis"]["semantic_guard_auxiliary"]["unresolved_count"] == 8


def test_r6_plan_is_frozen_and_rebuild_contract_is_stable():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    corpus = _load()
    assert plan["candidate_plan_sha256"] == f23o.plan_digest(plan)
    assert corpus["candidate_plan_sha256"] == plan["candidate_plan_sha256"]
    assert corpus["candidate_plan"] == plan
    assert corpus["source_v7_fixture_sha256"] == hashlib.sha256((FIXTURES / "evaluator_v2_corpus_v7.json").read_bytes()).hexdigest()
    assert len(plan["candidate_order"]) == 32
    assert plan["candidate_order"] == [row["id"] for family in plan["families"] for row in family["candidates"]]


def test_lineage_split_and_family_native_witnesses_are_deterministic():
    corpus = _load()
    records = corpus["records"]
    assert len(records) == 32
    assert all(row["planned_split"] == f23o._split(row["source_lineage_id"]) for row in records)
    for lineage in corpus["source_lineage_split"]:
        assert len({row["planned_split"] for row in records if row["source_lineage_id"] == lineage}) == 1
    effective = corpus["effective_preference_representatives"]
    assert len(effective) == corpus["coverage"]["combined_effective"]
    assert all(row["status"] == "PREFERENCE_STRONG" for row in effective)
    assert all(row["mechanic_witness"] for row in effective)
    assert all(len(row["wdl_partition"]) >= 2 for row in effective)
    assert corpus["coverage"]["mechanic_witness_coverage"] == len(effective)


def test_exact_certificates_are_complete_balanced_and_unresolved_never_strong():
    corpus = _load()
    for row in corpus["records"]:
        if row["status"] == "UNRESOLVED":
            assert row["strong"] is False
        if row["status"] == "PREFERENCE_STRONG":
            stats = row["solver_stats"]
            assert len(row["root_action_values"]) == stats["root_actions"]
            assert all(item["value"] in {"WIN", "DRAW", "LOSS"} for item in row["root_action_values"])
            assert stats["pushes"] == stats["pops"]
            assert stats["runtime_pushes"] == stats["runtime_pops"]
            assert stats["final_runtime_depth"] == 0
            assert len(row["decision_certificate_fingerprint"]) == 64
    assert not (set(corpus["all_equal_diagnostic_ids"]) & {row["id"] for row in corpus["effective_preference_representatives"]})


def test_combined_gate_and_leakage_accounting_are_exposed():
    corpus = _load()
    effective = corpus["effective_preference_representatives"]
    dev = [row for row in effective if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in effective if row["planned_split"] == "HOLDOUT"]
    assert len(dev) == 23
    assert len(holdout) == 5
    assert len(Counter(row["construction_family"] for row in dev)) == 4
    assert len(Counter(row["mechanic_family"] for row in dev)) == 4
    assert len(Counter(row["construction_family"] for row in holdout)) == 3
    assert len(corpus["coverage"]["wdl_partition_signatures_development"]) == 3
    assert corpus["excluded_source_lineage_leakage_ids"] == []
    assert len(corpus["excluded_behavioral_leakage_orbit_ids"]) == 1
    assert corpus["advancement_gate"]["passes"] is False
    assert corpus["selected_next_boundary"] == "F23P_REFERENCE_PREFERENCE_CORPUS_R7"
    assert corpus["production_changed"] is False
    assert corpus["reference_independence"]["forbidden_inputs_consulted"] is False


def test_historical_v1_to_v7_and_capability_artifacts_remain_unchanged():
    for name, expected in HISTORICAL.items():
        assert hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() == expected, name
    assert hashlib.sha256((FIXTURES / "evaluator_v2_corpus_v7.json").read_bytes()).hexdigest() == "57d0d40ad4e74815ca1c542c2fa680750ea8a6411e47249a3892f23954dd064b"


def test_v8_builder_is_reference_only_and_does_not_open_forbidden_sources():
    source = (ROOT / "scripts" / "build_f23o_preference_corpus_r6.py").read_text(encoding="utf-8")
    assert "exact_generic_preference_solver_v3" in source
    assert "exact_generic_preference_solver_v2" not in source
    assert "ADR-040" not in source
    assert "AlphaSho" not in source
    assert "Shogi" not in source

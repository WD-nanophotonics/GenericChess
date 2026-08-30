"""Durable contracts for the F23N independent exact preference corpus."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts import build_f23n_preference_corpus_r5 as f23n


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v7.json"
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
    "f23m_solver_capability_v4.json": "802342533ea7efb8b79f4ef2a2d922c928f20e4ef70c39f9da6d14e2ddb37ec2",
    "f23m_solver_capability_v4r1.json": "2419f2393516f6d7f4e2971483dd0e49560009e1dd0e3aa6c4b5fa8665c3088f",
    "f23m_solver_capability_v4r1_full.json": "90fbb87ede90d6a8c2416a976772cd4a36aa1307b5238f13c97a9be8b5c39b14",
}


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_frozen_plan_and_source_family_split_are_reproducible():
    corpus = _load()
    assert corpus["schema_version"] == 7
    assert corpus["candidate_plan_sha256"] == f23n.plan_digest()
    assert len(corpus["candidate_plan"]) == 5
    assert all(len(item["parameters"]) == f23n.MAX_CANDIDATES_PER_FAMILY for item in corpus["candidate_plan"])
    for record in corpus["records"]:
        source = record["source_family_id"]
        assert record["planned_split"] == f23n._split_for_source(source)
    assert all(len({row["planned_split"] for row in corpus["records"] if row["source_family_id"] == source}) == 1 for source in corpus["source_family_split"])


def test_preference_certificates_are_exact_complete_and_balanced():
    corpus = _load()
    effective = corpus["effective_preference_representatives"]
    assert effective
    assert all(row["status"] == "PREFERENCE_STRONG" for row in effective)
    assert all(len(row["wdl_partition"]) >= 2 for row in effective)
    assert all(row["ruleset_fingerprint"] for row in effective)
    assert all(len(row["root_action_values"]) == row["solver_stats"]["root_actions"] for row in effective)
    assert all({item["value"] for item in row["root_action_values"]} == set(row["wdl_partition"]) for row in effective)
    assert all(isinstance(row["solver_stats"]["unresolved"], dict) for row in effective)
    assert all(row["solver_stats"]["pushes"] == row["solver_stats"]["pops"] for row in effective)
    assert all(row["solver_stats"]["runtime_pushes"] == row["solver_stats"]["runtime_pops"] for row in effective)
    assert all(row["solver_stats"]["final_runtime_depth"] == 0 for row in effective)
    assert all(len(row["decision_certificate_fingerprint"]) == 64 for row in effective)


def test_witnesses_and_exclusions_preserve_mechanic_and_orbit_contracts():
    corpus = _load()
    witness_kinds = {
        "ordinary_anchor_movement": "root_terminal_witness",
        "capture_recapture_tactics": "root_capture",
        "drop_hand_tactics": "root_drop",
        "promotion_choice": "root_promotion_choice",
        "semantic_guard_auxiliary": "root_semantic_action",
    }
    effective_ids = {row["id"] for row in corpus["effective_preference_representatives"]}
    assert not ({row["id"] for row in corpus["non_preference_all_equal_records"]} & effective_ids)
    assert not corpus["excluded_behavioral_orbit_ids"]
    assert not corpus["excluded_source_family_ids"]
    for row in corpus["effective_preference_representatives"]:
        witness = row["mechanic_witness"]
        assert witness["kind"] == witness_kinds[row["construction_family"]]
        assert witness["action"] in [item["action"] for item in row["root_action_values"]]
        if row["construction_family"] == "drop_hand_tactics":
            assert witness["action"]["kind"] == "drop"
        elif row["construction_family"] == "promotion_choice":
            assert witness["action"]["promotion_target_id"] is not None
        elif row["construction_family"] == "semantic_guard_auxiliary":
            assert witness["action"]["kind"].startswith("semantic_")


def test_gate_and_boundary_are_derived_without_cross_family_leakage():
    corpus = _load()
    effective = corpus["effective_preference_representatives"]
    dev = [row for row in effective if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in effective if row["planned_split"] == "HOLDOUT"]
    assert len(dev) == corpus["coverage"]["development"]
    assert len(holdout) == corpus["coverage"]["holdout"]
    assert len(Counter(row["construction_family"] for row in dev)) == corpus["coverage"]["development_construction_families"]
    assert len(Counter(row["mechanic_family"] for row in dev)) == corpus["coverage"]["development_mechanic_families"]
    assert corpus["advancement_gate"]["passes"] is False
    assert corpus["selected_next_boundary"] == "F23O_REFERENCE_PREFERENCE_CORPUS_R6"
    assert corpus["production_changed"] is False
    assert corpus["evaluator_inspection"] is False
    assert corpus["shogi_reference_opened"] is False


def test_historical_artifacts_remain_byte_identical():
    fixture_dir = FIXTURE.parent
    for name, expected in HISTORICAL.items():
        assert hashlib.sha256((fixture_dir / name).read_bytes()).hexdigest() == expected, name


def test_plan_has_no_forbidden_reference_or_production_dependency():
    source = (ROOT / "scripts" / "build_f23n_preference_corpus_r5.py").read_text(encoding="utf-8")
    assert "exact_generic_preference_solver_v3" in source
    assert "exact_generic_preference_solver_v2" not in source
    assert "ADR-040" not in source
    assert "AlphaSho" not in source
    assert "Shogi" not in source

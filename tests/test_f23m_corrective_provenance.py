"""Provenance and durable-evidence contracts for F23M corrective R1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.audit_f23m_threshold_runtime_solver import summarize_report


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures"

FROZEN_FIXTURE_SHA256 = {
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
}


def test_v4r1_summary_is_derived_from_authoritative_full_report():
    full = json.loads((FIXTURES / "f23m_solver_capability_v4r1_full.json").read_text(encoding="utf-8"))
    summary = json.loads((FIXTURES / "f23m_solver_capability_v4r1.json").read_text(encoding="utf-8"))
    assert full["summary"] == summary
    assert summarize_report(full) == summary
    assert full["baseline_sandbox_sha"] == "d03e9fa6ca9d89cb22555393103d0eacaf9d762d"
    assert full["solver_version"]
    assert len(full["benchmark_plan_digest"]) == 64
    assert full["representative_ids"] == [row["representative_id"] for row in full["rows"]]


def test_v4r1_attempts_and_certificates_are_complete_and_derived():
    full = json.loads((FIXTURES / "f23m_solver_capability_v4r1_full.json").read_text(encoding="utf-8"))
    required = {"strong", "unresolved_reason", "states_expanded", "legal_actions_enumerated", "root_branching", "pushes", "pops", "runtime_pushes", "runtime_pops", "threshold_tt_hits", "tt_entries", "proof_short_circuits", "proof_depth", "repetition_adjudications", "perpetual_check_adjudications", "history_key_mode"}
    for row in full["rows"]:
        attempts = row["attempts"]
        assert [attempt["tier"] for attempt in attempts] == ["SMALL"] or [attempt["tier"] for attempt in attempts] == ["SMALL", "MEDIUM"] or [attempt["tier"] for attempt in attempts] == ["SMALL", "MEDIUM", "LARGE"]
        resolved = next((attempt for attempt in attempts if attempt["result"]["strong"]), None)
        assert row["first_resolving_tier"] == (resolved["tier"] if resolved else None)
        assert row["selected_result_tier"] == (resolved["tier"] if resolved else attempts[-1]["tier"])
        for attempt in attempts:
            result = attempt["result"]
            assert required <= result.keys()
            if result["strong"]:
                assert result["root_action_certificate_complete"] is True
                assert result["root_action_values"]
                assert all(item["value"] in {"WIN", "DRAW", "LOSS"} for item in result["root_action_values"])
                assert result["runtime_balanced_derived"] is True
                assert result["profile_seconds"]["total_seconds"] > 0
                assert result["profile_proportions"]["proof_bookkeeping_seconds"] >= 0
            if result["unresolved_reason"] == "REFERENCE_SOLVE_UNRESOLVED:time_cap":
                assert result["blocker"] == "UNCLASSIFIED_TIME_CAP"
                assert result["states_expanded"] is None
            if result["states_expanded"] is not None:
                assert result["runtime_balanced_derived"] is True or not result["strong"]


def test_frozen_f23m_and_prior_artifacts_are_byte_identical():
    for name, expected in FROZEN_FIXTURE_SHA256.items():
        actual = hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()
        assert actual == expected, name

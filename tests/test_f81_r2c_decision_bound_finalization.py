"""Contract tests for F81-R2C zero-compute finalization."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "f81_final_confirmation" / "final_strength_evidence.json"
AUDIT = ROOT / "artifacts" / "f81_final_confirmation" / "f81_r1_time_cap_audit.json"
REPORT = ROOT / "docs" / "architecture" / "GENERICCHESS_F81_R2B_ZERO_COMPUTE_DECISION_BOUND.md"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f81_r2c_decision_bound_is_durable_and_fail_safe():
    evidence = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    bound = evidence["decision_bound"]

    assert evidence["schema"] == "generic-chess-f81-final-strength-evidence-v3-decision-bound"
    assert evidence["classification"] == "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED"
    assert evidence["confirmation_method"] == "ZERO_COMPUTE_WORST_CASE_DECISION_BOUND"
    assert evidence["physical_pair_completion"] == 7
    assert evidence["decision_pair_count"] == 8
    assert evidence["excluded_pair_indices"] == [5]
    assert evidence["excluded_pair_reason"] == "TIME_BUDGET_CAP_CONTRACT_MISMATCH"
    assert evidence["decision_bound_covers_excluded_pairs"] is True
    assert evidence["pair5_corrective_compute_status"] == "CANCELLED_NO_DECISION_VALUE"
    assert evidence["final_decision_bound"]["path"] == "artifacts/f81_final_confirmation/final_decision_bound.json"

    assert evidence["retained_clean_pair_indices"] == [0, 1, 2, 3, 4, 6, 7]
    assert bound["clean_pair_scores"] == [1.0, 0.5, 0.5, 0.0, 0.5, 1.0, 0.75]
    assert bound["clean_score_sum"] == 4.25
    assert bound["replacement_score_domain"] == [0.0, 1.0]
    assert bound["worst_case_completed_mean"] == 0.53125
    assert bound["worst_case_completed_mean"] > bound["mean_threshold"]
    assert bound["clean_better_tied_worse"] == [3, 3, 1]
    assert bound["worst_case_better_tied_worse"] == [3, 3, 2]
    assert bound["worst_case_better_minus_worse_margin"] == 1
    assert bound["strength_gate_forced_for_all_valid_replacements"] is True


def test_f81_r2c_binds_exact_prior_evidence_and_never_restores_pair5_score():
    evidence = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert _sha(AUDIT) == evidence["time_cap_audit"]["content_sha256"]
    assert _sha(REPORT) == evidence["r2b_report"]["content_sha256"]
    assert evidence["r2a_canonical_evidence"]["content_sha256"] == "e6ed1819a51cc6ae8e16167a42788786548e5a955679ae261910a7d9cf591a25"
    assert evidence["invalidated_diagnostic_scores"]["fresh_pair_scores"][5] == 0.75
    assert evidence["excluded_pair_indices"] == [5]
    assert evidence["champion_before"] == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert evidence["champion_after"] == "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
    assert ".generic_chess_flow" not in ARTIFACT.read_text(encoding="utf-8")

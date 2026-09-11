"""Contract tests for F81-R2C zero-compute finalization."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "f81_final_confirmation" / "final_strength_evidence.json"
AUDIT = ROOT / "artifacts" / "f81_final_confirmation" / "f81_r1_time_cap_audit.json"
REPORT = ROOT / "docs" / "architecture" / "GENERICCHESS_F81_R2B_ZERO_COMPUTE_DECISION_BOUND.md"
FINAL_BOUND = ROOT / "artifacts" / "f81_final_confirmation" / "final_decision_bound.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f81_r2c_decision_bound_is_durable_and_fail_safe():
    evidence = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    bound = evidence["decision_bound"]
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    clean_pairs = [pair for pair in audit["pairs"] if not pair["cap_contaminated"]]
    clean_indices = [pair["pair_index"] for pair in clean_pairs]
    clean_scores = [
        (pair["game_child_owner0"]["child_points"] + pair["game_child_owner1"]["child_points"]) / 2
        for pair in clean_pairs
    ]
    clean_counts = [
        sum(score > 0.5 for score in clean_scores),
        sum(score == 0.5 for score in clean_scores),
        sum(score < 0.5 for score in clean_scores),
    ]
    replacement_domain = [0.0, 1.0]
    worst_mean = (sum(clean_scores) + min(replacement_domain)) / 8
    worst_counts = [clean_counts[0], clean_counts[1], clean_counts[2] + 1]

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
    assert evidence["final_decision_bound"]["content_sha256"] == _sha(FINAL_BOUND)

    assert clean_indices == [0, 1, 2, 3, 4, 6, 7]
    assert evidence["retained_clean_pair_indices"] == clean_indices
    assert bound["clean_pair_scores"] == clean_scores
    assert bound["clean_score_sum"] == sum(clean_scores) == 4.25
    assert bound["replacement_score_domain"] == replacement_domain
    assert bound["worst_case_completed_mean"] == worst_mean == 0.53125
    assert bound["worst_case_completed_mean"] > bound["mean_threshold"]
    assert bound["mean_gate_margin"] == worst_mean - bound["mean_threshold"] == 0.03125
    assert bound["clean_better_tied_worse"] == clean_counts == [3, 3, 1]
    assert bound["worst_case_better_tied_worse"] == worst_counts == [3, 3, 2]
    assert bound["worst_case_better_minus_worse_margin"] == 1
    assert bound["strength_gate_forced_for_all_valid_replacements"] is True


def test_f81_r2c_binds_exact_prior_evidence_and_never_restores_pair5_score():
    evidence = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    bound = json.loads(FINAL_BOUND.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    contaminated = [pair for pair in audit["pairs"] if pair["cap_contaminated"]]

    assert _sha(AUDIT) == evidence["time_cap_audit"]["content_sha256"]
    assert _sha(REPORT) == evidence["r2b_report"]["content_sha256"]
    assert _sha(FINAL_BOUND) == evidence["final_decision_bound"]["content_sha256"]
    assert bound["r2a_canonical_evidence_checkpoint"] == "9dbd5e3e82bdf471d63eb1c13c54f33427c84761"
    assert bound["r2a_canonical_evidence_path"] == "artifacts/f81_final_confirmation/final_strength_evidence.json"
    assert bound["r2a_canonical_evidence_sha256"] == "e6ed1819a51cc6ae8e16167a42788786548e5a955679ae261910a7d9cf591a25"
    assert bound["time_cap_audit_path"] == "artifacts/f81_final_confirmation/f81_r1_time_cap_audit.json"
    assert evidence["r2a_canonical_evidence"]["content_sha256"] == "e6ed1819a51cc6ae8e16167a42788786548e5a955679ae261910a7d9cf591a25"
    assert [pair["pair_index"] for pair in contaminated] == [5]
    assert evidence["invalidated_diagnostic_scores"]["fresh_pair_scores"][5] == contaminated[0]["pair_score"] == 0.75
    assert evidence["excluded_pair_indices"] == [5]
    assert evidence["champion_before"] == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert evidence["champion_after"] == "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
    assert ".generic_chess_flow" not in ARTIFACT.read_text(encoding="utf-8")
    assert ".generic_chess_flow" not in FINAL_BOUND.read_text(encoding="utf-8")

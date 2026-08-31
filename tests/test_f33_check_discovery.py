import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _result():
    path = ROOT / "tests" / "fixtures" / "f33_check_discovery_audit.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_f33_h33a_audit_is_complete_without_production_change():
    path, result = _result()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "e65300346bb7be48bcf933a163d25f5700fe7c2b93efc5b577b491eee973f25c"
    assert result["status"] == "PASS"
    assert result["production_changed"] is False
    assert result["retained_candidate"] == "NONE"
    assert result["next_boundary"] == "F34_QUIESCENCE_BUDGET_ARCHITECTURE"
    assert all(result["flags"].values()) is False
    assert result["flags"]["SEMANTIC_CHECKING_ACTION_DISCOVERY_FASTPATH_RETAINED"] is False


def test_f33_candidates_pass_exact_parity_and_fail_only_retention_gate():
    result = _result()[1]
    gates = result["gates"]
    assert gates["candidate_a_classifier_parity"] is True
    assert gates["candidate_a_fixed_result_parity"] is True
    assert gates["candidate_b_classifier_parity"] is True
    assert gates["candidate_b_fixed_result_parity"] is True
    assert gates["candidate_b_structural_gate"] is True
    assert gates["candidate_b_performance_gate"] is False
    assert gates["candidate_b_root_accessibility_gate"] is False
    assert gates["candidate_b_retention"] is False
    assert result["candidate_b_committed_push_reduction"] == {"512": 1.0, "2048": 1.0}


def test_f33_discovery_counts_and_history_fallbacks_are_recorded():
    result = _result()[1]
    totals = result["classifier_totals"]
    assert totals["BASELINE"]["512"]["mismatches"] == 0
    assert totals["CANDIDATE_A_POST_PUSH_GAVE_CHECK"]["2048"]["mismatches"] == 0
    assert totals["CANDIDATE_B_SEMANTIC_PREVIEW"]["512"]["preview_transitions"] == 28307
    assert totals["CANDIDATE_B_SEMANTIC_PREVIEW"]["2048"]["preview_transitions"] == 87780
    assert result["history_terminal_witnesses"]["opaque_history"]
    assert result["history_terminal_witnesses"]["continuous_check"]

from scripts.f87a_phase_gate_reconciliation import reconcile
from scripts.f87a_r9_western_dynamic_discovery import run as run_r9


def test_f87a_reconciliation_satisfies_frozen_playability_scope_without_opening_d_or_e(tmp_path):
    r9_result = run_r9(output_dir=tmp_path / "r9")
    result = reconcile(r9_result)
    assert result["charter"]["declared_target"] == "PLAYABILITY"
    assert result["charter"]["required_layers"] == ["A", "B", "C"]
    assert result["scope_decision"] == "PLAYABILITY_SCOPE_SATISFIED"
    assert result["layers"]["A"]["status"] == "PASS"
    assert result["layers"]["B"]["status"] == "DIAGNOSTIC_ONLY"
    assert result["layers"]["C"]["status"] == "PASS"
    assert result["deferred_follow_on"] == {"D": "DEFERRED_IN_F87A", "E": "DEFERRED_IN_F87A"}
    assert result["promotion_decision"] == "NOT_GRANTED_BY_SCOPE_RECONCILIATION"


def test_f87a_reconciliation_rejects_unreconciled_termination_evidence():
    unreconciled = {
        "dynamic_viability_pass": False,
        "search_budget_censored_count": 0,
        "terminal_discovery_count": 1,
    }
    try:
        reconcile(unreconciled)
    except ValueError as exc:
        assert "termination-viability" in str(exc)
    else:
        raise AssertionError("unreconciled R9 evidence must fail closed")

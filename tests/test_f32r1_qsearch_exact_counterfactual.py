import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _result():
    path = ROOT / "tests" / "fixtures" / "f32r1_qsearch_exact_counterfactual.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_f32r1_executable_counterfactual_is_published_evidence():
    path = ROOT / "tests" / "fixtures" / "f32r1_qsearch_exact_counterfactual.json"
    result = _result()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "0805a97b12de1fd011386a11e1e0a532e13c42b44266269671a2499f29259b88"
    assert result["status"] == "PASS"
    assert result["production_changed"] is False
    assert result["f32_manifest_sha256"] == "dfd8b8394ba25136b650450b25e3429c3487a9de05d25d4c253c2ecebc6e6b2b"
    assert result["f32_result_sha256"] == "878dccd45d2d9bf325d26d1947a5ee8e85b8005176e3dbfdf0772c9e46becd56"
    assert all(result["flags"].values())


def test_f32r1_parity_and_derived_boundary_are_gate_backed():
    result = _result()
    gates = result["derived_gates"]
    assert gates["lazy_value_parity"] is True
    assert gates["classifier_parity"] is True
    assert gates["classifier_parity_mismatches"] == 0
    assert gates["fixed_512_complete_generation_calls_avoided"] > 0
    assert gates["fixed_512_complete_generation_call_savings_fraction"] >= 0.25
    assert gates["lazy_materiality_gate"] is False
    assert gates["checking_discovery_fastpath_gate"] is True
    assert gates["next_boundary"] == "F33_SEMANTIC_CHECKING_ACTION_DISCOVERY_FASTPATH"
    assert gates["qnode_cap_semantics"] == "MIXED"


def test_f32r1_exact_classifier_covers_required_categories_and_witnesses():
    result = _result()
    for budget in ("512", "2048"):
        totals = result["derived_gates"]["classification_totals"][budget]
        assert totals["input_candidates"] == totals["total_accepted"] + totals["total_rejected"]
        assert totals["classification_pushes"] == (
            totals["terminal_child_push_accepted"]
            + totals["checking_board_push_accepted"]
            + totals["quiet_board_push_rejected"]
            + totals["checking_drop_push_accepted"]
            + totals["nonchecking_drop_push_rejected"]
            + totals["other_rejected"]
        )
        assert totals["expanded_noncheck_qnodes"] > 0
        assert totals["pushes_per_expanded_noncheck_qnode"] > 0
        assert totals["checking_board_push_accepted"] > 0
        assert totals["checking_drop_push_accepted"] > 0
        assert totals["quiet_board_push_rejected"] > 0
        assert totals["nonchecking_drop_push_rejected"] > 0
    witnesses = result["coverage"]["branch_witnesses"]
    assert {name for name, row in witnesses.items() if row["executed"]} == {
        "terminal_root",
        "terminal_child",
        "declaration_win",
        "declaration_restart",
        "declaration_loss",
        "in_check_full_evasion",
    }

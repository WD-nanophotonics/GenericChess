"""The pawn control value affects a shallow choice without proving quality."""

from scripts.audit_chess_pawn_value_ablation import run_probe


def test_pawn_value_ablation_changes_no_qsearch_choice_only():
    result = run_probe()
    assert result["classification"] == "PAWN_VALUE_SEARCH_SENSITIVITY_PASS"
    rows = result["rows"]
    assert rows["p4_q0"]["action"]["from"] == [1, 4]
    assert rows["p4_q0"]["action"]["to"] == [0, 4]
    assert rows["p0_q0"]["action"]["from"] == [3, 0]
    assert rows["p0_q0"]["action"]["to"] == [4, 0]
    assert rows["p4_q4"]["action"] == rows["p0_q4"]["action"]

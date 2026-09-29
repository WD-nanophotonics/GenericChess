"""Exact short-mate certificate is independent of material search output."""

import pytest

from generic_chess.native import native_available
from scripts.audit_chess_mate2_qsearch import run_probe


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_mate2_root_distinguishes_two_certified_mate_horizons():
    result = run_probe()
    assert result["classification"] == "MATE2_QSEARCH_BOUNDARY_PASS"
    assert result["certificate"]["generated_successors"] <= 8192
    assert result["certificate"]["label_counts"] == {
        "FORCED_MATE_IN_TWO": 6,
        "IMMEDIATE_DRAW": 14,
        "UNRESOLVED": 13,
    }
    assert result["native_selected_mate2_certificate"]["reply_count"] == 1
    assert result["native_selected_mate2_certificate"]["all_replies_have_mate"]
    later = result["q0_selected_later_mate_certificate"]
    assert later["generated_successors"] <= 8192
    assert later["forced_mate_within_three_plies_from_root"] is False
    assert later["forced_mate_within_five_plies_from_root"] is True
    assert result["native_q0_selected_later_line"] == {
        "black_reply_counts": [1, 1],
        "terminal": {"status": "checkmate", "winner": 0},
    }
    assert result["python"]["d2_q4"]["certified_label"] == "FORCED_MATE_IN_TWO"
    assert result["python"]["d2_q0"]["certified_label"] == "UNRESOLVED"
    assert result["python"]["d2_q0"]["action"] == result["native_no_quiescence"]["d2_q0"]["action"]

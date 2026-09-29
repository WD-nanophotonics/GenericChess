"""A legal capture and a quiet short mate can both preserve exact winning W/D/L."""

import pytest

from generic_chess.native import native_available
from scripts.audit_chess_material_change_outcome import run_probe


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_material_changing_capture_is_not_a_wdl_distinction_here():
    result = run_probe()
    assert result["classification"] == "MATERIAL_CHANGE_BOTH_WIN_PASS"
    assert result["black_pawns_before_after_q0"] == [1, 0]
    assert result["python_d2_q0"]["short_label"] == "UNRESOLVED"
    assert result["python_d2_q4"]["short_label"] == "FORCED_MATE_IN_TWO"
    assert result["q0_later_certificate"]["forced_mate_within_five_plies_from_root"]
    assert result["native_d2_q0"]["action"] == result["python_d2_q0"]["action"]

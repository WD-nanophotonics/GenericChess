"""Executable pawn-drop check for an omitted state guard."""

from scripts.audit_shogi_pawn_drop_boundary import audit


def test_same_file_unpromoted_pawn_removes_exactly_six_coarse_drops():
    result = audit()
    assert result["P"] == {
        "intrinsic_count": 70,
        "legal_count": 64,
        "intrinsic_only": [13, 22, 31, 49, 58, 67],
        "legal_only": [],
    }
    assert result["TP"] == {
        "intrinsic_count": 70,
        "legal_count": 70,
        "intrinsic_only": [],
        "legal_only": [],
    }

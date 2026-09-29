"""Executable control for the pawn-drop-mate postcondition."""

from scripts.audit_shogi_pawn_drop_mate_boundary import audit


def test_goal_achieving_pawn_drop_is_forbidden_when_it_mates():
    assert audit() == {
        "unprotected": {
            "coarse_target_present": True,
            "legal_drop_present": True,
            "prospective_opponent_in_check": True,
            "prospective_reply_count": 1,
            "prospective_terminal": "ongoing",
        },
        "protected": {
            "coarse_target_present": True,
            "legal_drop_present": False,
            "prospective_opponent_in_check": True,
            "prospective_reply_count": 0,
            "prospective_terminal": "checkmate",
        },
    }

"""Only the pawn-drop action form is barred for a shared mate position."""

from scripts.audit_shogi_pawn_mate_action_form import audit


def test_drop_and_advance_to_same_mate_position_have_different_legality():
    result = audit()
    assert result["same_postmove_position"] is True
    assert result["pawn_drop_legal"] is False
    assert result["pawn_advance_legal"] is True
    assert result["postmove_terminal"] == "checkmate"
    assert result["postmove_reply_count"] == 0

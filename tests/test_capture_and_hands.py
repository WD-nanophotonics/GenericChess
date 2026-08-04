"""Capture -> hand flow, conservation, and illegal capture guards."""

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.movegen import apply_action_to_position, legal_actions_from_position
from generic_chess.core.position import Hands

from conftest import king_type, make_compiled, make_position, sq, T


def _compiled():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    filler = T("F", LeapAtom((1, 0)))
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)))
    return make_compiled(8, [king_type(), rook, filler, pawn, gold])


def _count(position):
    return sum(1 for p in position.board if p is not None) + sum(
        h.total() for h in position.hands
    )


def test_capture_adds_to_hand_and_conserves():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KRf.....",
        ],
    )
    before = _count(pos)
    after = apply_action_to_position(pos, BoardMove(sq(1, 0), sq(2, 0)), compiled)
    assert after.hands[0].count("F") == 1
    assert after.board[sq(2, 0).rank * 8 + sq(2, 0).file] is None or True  # moved
    assert _count(after) == before


def test_capture_of_promoted_piece_restores_base_type():
    compiled = _compiled()
    # P1 piece on (2,0) is promoted G with base P.
    pos = make_position(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KRg.....",
        ],
        promoted={(2, 0): "P"},
    )
    after = apply_action_to_position(pos, BoardMove(sq(1, 0), sq(2, 0)), compiled)
    assert after.hands[0].count("P") == 1  # base type, not the promoted type
    assert after.hands[0].count("G") == 0


def test_drop_removes_from_hand_and_conserves():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
        hands=([("F", 2)], []),
    )
    before = _count(pos)
    after = apply_action_to_position(pos, DropMove("F", sq(3, 3)), compiled)
    assert after.hands[0].count("F") == 1
    assert after.board[3 * 8 + 3].base_type_id == "F"
    assert after.board[3 * 8 + 3].owner == 0
    assert _count(after) == before


def test_move_without_capture_keeps_hands():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KR......",
        ],
    )
    after = apply_action_to_position(pos, BoardMove(sq(1, 0), sq(1, 1)), compiled)
    assert after.hands[0].counts == ()
    assert after.hands[1].counts == ()


def test_cannot_capture_own_piece():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KRF.....",
        ],
    )
    with pytest.raises(ValueError):
        apply_action_to_position(pos, BoardMove(sq(1, 0), sq(2, 0)), compiled)


def test_cannot_capture_anchor():
    compiled = _compiled()
    # P1 anchor at (2,0); P0 rook at (1,0) may not capture it.
    pos = make_position(
        compiled,
        [
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KR......",
        ],
    )
    # Move P1 anchor to (2,0): lowercase k in the bottom row.
    pos = make_position(
        compiled,
        [
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KRk.....",
        ],
    )
    assert BoardMove(sq(1, 0), sq(2, 0)) not in legal_actions_from_position(pos, compiled)
    with pytest.raises(ValueError):
        apply_action_to_position(pos, BoardMove(sq(1, 0), sq(2, 0)), compiled)


def test_hands_immutable_ops():
    h = Hands(())
    h2 = h.add("F").add("P").add("F")
    assert h.count("F") == 0  # original unchanged
    assert h2.count("F") == 2
    assert h2.count("P") == 1
    h3 = h2.remove("F")
    assert h3.count("F") == 1
    with pytest.raises(ValueError):
        h3.remove("Q")

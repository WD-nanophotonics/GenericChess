"""Capture -> hand flow, conservation, and illegal capture guards."""

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.movegen import _apply_action_unchecked, legal_actions_from_position
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.position import Hands
from generic_chess.core.transition import apply_action

from conftest import king_type, make_compiled, make_position, make_state, sq, T


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
    state = make_state(
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
    before = _count(state.position)
    after = apply_action(state, BoardMove(sq(1, 0), sq(2, 0)), compiled)
    assert after.position.hands[0].count("F") == 1
    assert after.position.board[2].base_type_id == "R"
    assert _count(after.position) == before


def test_capture_of_promoted_piece_restores_base_type():
    compiled = _compiled()
    state = make_state(
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
    after = apply_action(state, BoardMove(sq(1, 0), sq(2, 0)), compiled)
    assert after.position.hands[0].count("P") == 1  # base type, not promoted type
    assert after.position.hands[0].count("G") == 0


def test_drop_removes_from_hand_and_conserves():
    compiled = _compiled()
    state = make_state(
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
    before = _count(state.position)
    after = apply_action(state, DropMove("F", sq(3, 3)), compiled)
    assert after.position.hands[0].count("F") == 1
    assert after.position.board[3 * 8 + 3].base_type_id == "F"
    assert after.position.board[3 * 8 + 3].owner == 0
    assert _count(after.position) == before


def test_move_without_capture_keeps_hands():
    compiled = _compiled()
    state = make_state(
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
    after = apply_action(state, BoardMove(sq(1, 0), sq(1, 1)), compiled)
    assert after.position.hands[0].counts == ()
    assert after.position.hands[1].counts == ()


def test_public_apply_action_rejects_capture_of_own_piece():
    compiled = _compiled()
    state = make_state(
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
    with pytest.raises(IllegalActionError):
        apply_action(state, BoardMove(sq(1, 0), sq(2, 0)), compiled)


def test_unchecked_executor_guards_own_capture():
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
    with pytest.raises(IllegalActionError):
        _apply_action_unchecked(pos, BoardMove(sq(1, 0), sq(2, 0)), compiled)


def test_public_apply_action_rejects_anchor_capture():
    compiled = _compiled()
    # P1 anchor at (2,0); P0 rook at (1,0) may not capture it.
    state = make_state(
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
    assert BoardMove(sq(1, 0), sq(2, 0)) not in legal_actions_from_position(
        state.position, compiled
    )
    with pytest.raises(IllegalActionError):
        apply_action(state, BoardMove(sq(1, 0), sq(2, 0)), compiled)


def test_unchecked_executor_guards_anchor_capture():
    compiled = _compiled()
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
    with pytest.raises(IllegalActionError):
        _apply_action_unchecked(pos, BoardMove(sq(1, 0), sq(2, 0)), compiled)


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

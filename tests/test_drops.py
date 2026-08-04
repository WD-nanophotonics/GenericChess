"""Drop rules: masks, empty squares, checks, mate by drop."""

import pytest

from generic_chess.core.actions import DropMove
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.movegen import apply_action_to_position, legal_actions_from_position
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action

from conftest import (
    king_type,
    make_compiled,
    make_position,
    make_state,
    sq,
    T,
)


def _pawn_knight_compiled():
    pawn = T("P", LeapAtom((0, 1)))
    knight = T("N", LeapAtom((1, 2)), LeapAtom((-1, 2)))
    return make_compiled(8, [king_type(), pawn, knight], auto_drop=True)


def test_drop_only_on_empty_square():
    compiled = _pawn_knight_compiled()
    pos2 = make_position(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KP......",
        ],
        hands=([("P", 1)], []),
    )
    with pytest.raises(ValueError):
        apply_action_to_position(pos2, DropMove("P", sq(1, 0)), compiled)


def test_drop_requires_piece_in_hand():
    compiled = _pawn_knight_compiled()
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
    )
    with pytest.raises(ValueError):
        apply_action_to_position(pos, DropMove("P", sq(3, 3)), compiled)


def test_pawn_like_drop_forbidden_on_last_rank():
    compiled = _pawn_knight_compiled()
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
        hands=([("P", 1)], []),
    )
    actions = legal_actions_from_position(pos, compiled)
    drops = [a for a in actions if isinstance(a, DropMove) and a.base_type_id == "P"]
    assert drops and all(a.to_square.rank != 7 for a in drops)
    assert DropMove("P", sq(4, 6)) in actions


def test_knight_like_drop_forbidden_on_last_two_ranks():
    compiled = _pawn_knight_compiled()
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
        hands=([("N", 1)], []),
    )
    actions = legal_actions_from_position(pos, compiled)
    drops = [a for a in actions if isinstance(a, DropMove) and a.base_type_id == "N"]
    assert drops and all(a.to_square.rank < 6 for a in drops)


def test_drop_does_not_promote_immediately():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)))
    compiled = make_compiled(8, [king_type(), pawn, gold])
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
        hands=([("P", 1)], []),
    )
    after = apply_action_to_position(pos, DropMove("P", sq(4, 6)), compiled)
    piece = after.board[6 * 8 + 4]
    assert piece.base_type_id == "P"
    assert piece.current_type_id == "P"
    assert not piece.promoted


def test_drop_can_escape_check():
    pawn = T("P", LeapAtom((0, 1)))
    rook = T("R", RayAtom((0, 1)))
    compiled = make_compiled(8, [king_type(), rook, pawn], auto_drop=True)
    pos = make_position(
        compiled,
        [
            "....r...",  # rank 7
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "....K...",  # rank 0
        ],
        side_to_move=0,
        hands=([("P", 1)], []),
    )
    actions = legal_actions_from_position(pos, compiled)
    assert DropMove("P", sq(4, 3)) in actions  # blocks the check
    assert DropMove("P", sq(5, 5)) not in actions  # check unresolved


def test_drop_gives_check():
    down_ray = T("R", RayAtom((0, -1)))
    compiled = make_compiled(8, [king_type(), down_ray])
    # P1 king at (0,0); drop a downward ray at (0,3) -> checks file 0.
    pos = make_position(
        compiled,
        [
            ".......K",  # rank 7: P0 anchor
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "k.......",  # rank 0
        ],
        side_to_move=0,
        hands=([("R", 1)], []),
    )
    actions = legal_actions_from_position(pos, compiled)
    assert DropMove("R", sq(0, 3)) in actions
    after = apply_action_to_position(pos, DropMove("R", sq(0, 3)), compiled)
    from generic_chess.core.attacks import is_in_check

    assert is_in_check(after, 1, compiled)


def test_drop_mate():
    down_ray = T("R", RayAtom((0, -1)))
    compiled = make_compiled(8, [king_type(), down_ray])
    # P1 king cornered at (0,0): drop R at (0,3) checks file 0; P0 king at
    # (2,1) covers (1,0) and (1,1).
    pos = make_position(
        compiled,
        [
            "........",  # rank 7
            "........",
            "........",
            "........",
            "........",
            "........",
            "..K.....",  # rank 1
            "k.......",  # rank 0
        ],
        side_to_move=0,
        hands=([("R", 1)], []),
    )
    actions = legal_actions_from_position(pos, compiled)
    assert DropMove("R", sq(0, 3)) in actions
    state = make_state(
        compiled,
        [
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "..K.....",
            "k.......",
        ],
        side_to_move=0,
        hands=([("R", 1)], []),
    )
    after = apply_action(state, DropMove("R", sq(0, 3)), compiled)
    assert after.terminal_status.status is TerminalStatus.CHECKMATE
    assert after.terminal_status.winner == 0

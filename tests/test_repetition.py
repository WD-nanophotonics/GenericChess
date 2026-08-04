"""Repetition draws, key semantics, ply limit, and priority."""

from generic_chess.core.keys import position_key
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state

from conftest import (
    board_move,
    king_type,
    make_compiled,
    make_position,
    make_ruleset,
    T,
)


def _shuttle_compiled(repetition_limit=4, max_ply=512):
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    ruleset = make_ruleset(
        8,
        [king_type(), rook],
        lines=[
            ".......k",  # rank 7: P1 anchor
            "........",  # rank 6
            "....r...",  # rank 5: P1 rook at (4,5)
            "........",  # rank 4
            "........",  # rank 3
            "...R....",  # rank 2: P0 rook at (3,2)
            "........",  # rank 1
            "K.......",  # rank 0: P0 anchor
        ],
        repetition_limit=repetition_limit,
        max_ply=max_ply,
    )
    from generic_chess.rules.compiler import compile_ruleset

    return compile_ruleset(ruleset)


def _shuttle_moves():
    return [
        board_move(3, 2, 3, 3),  # P0 rook up
        board_move(4, 5, 4, 4),  # P1 rook down
        board_move(3, 3, 3, 2),  # P0 rook back
        board_move(4, 4, 4, 5),  # P1 rook back
    ]


def test_fourth_full_position_repetition_is_draw():
    compiled = _shuttle_compiled(repetition_limit=4)
    state = initial_state(compiled)
    moves = _shuttle_moves()
    for _ in range(3):
        for move in moves:
            state = apply_action(state, move, compiled)
    assert state.ply_count == 12
    assert state.terminal_status.status is TerminalStatus.REPETITION
    assert state.terminal_status.winner is None


def test_hand_difference_changes_position_key():
    compiled = _shuttle_compiled()
    lines = [
        ".......k",
        "........",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    a = make_position(compiled, lines, hands=([("R", 1)], []))
    b = make_position(compiled, lines)
    assert position_key(a, compiled) != position_key(b, compiled)


def test_side_to_move_changes_position_key():
    compiled = _shuttle_compiled()
    lines = [
        ".......k",
        "........",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    a = make_position(compiled, lines, side_to_move=0)
    b = make_position(compiled, lines, side_to_move=1)
    assert position_key(a, compiled) != position_key(b, compiled)


def test_base_lineage_changes_position_key():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    queen = T("Q", LeapAtom((1, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)))
    compiled = make_compiled(8, [king_type(), pawn, queen, gold], auto_promotion=True)
    lines = [
        ".......k",
        "........",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K..g....",
    ]
    a = make_position(compiled, lines, promoted={(3, 0): "P"})
    b = make_position(compiled, lines, promoted={(3, 0): "Q"})
    assert position_key(a, compiled) != position_key(b, compiled)


def test_max_ply_draw():
    compiled = _shuttle_compiled(repetition_limit=1000, max_ply=8)
    state = initial_state(compiled)
    moves = _shuttle_moves()
    for i in range(8):
        state = apply_action(state, moves[i % 4], compiled)
    assert state.ply_count == 8
    assert state.terminal_status.status is TerminalStatus.MAX_PLY
    assert state.terminal_status.winner is None


def test_default_max_ply_is_512():
    from generic_chess.rules.schema import RuleSet

    assert RuleSet().max_ply == 512
    assert RuleSet().repetition_limit == 4

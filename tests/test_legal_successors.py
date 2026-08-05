"""Core legal_successors: one-shot legal move generation with child states."""

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.errors import RuleSetMismatchError
from generic_chess.core.movegen import legal_actions
from generic_chess.core.position import GameState
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.core.transition import apply_action, legal_successors
from generic_chess.session.session import GameSession

from ai_fixtures import build_4x4_rooks, build_mate, build_promotion
from conftest import make_state


def test_legal_successors_match_legal_actions():
    compiled = build_4x4_rooks()
    state = GameSession(compiled).state
    pairs = legal_successors(state, compiled)
    assert [action for action, _ in pairs] == legal_actions(state, compiled)
    assert pairs


def test_children_equal_public_apply_action():
    compiled = build_4x4_rooks()
    state = GameSession(compiled).state
    for action, child in legal_successors(state, compiled):
        applied = apply_action(state, action, compiled)
        assert child.position == applied.position
        assert child.ply_count == applied.ply_count
        assert child.repetition_counts == applied.repetition_counts
        assert child.terminal_status == applied.terminal_status
        assert child.position.side_to_move == 1 - state.position.side_to_move
        assert child.ply_count == state.ply_count + 1


def test_terminal_state_yields_empty():
    compiled = build_4x4_rooks()
    state = GameSession(compiled).state
    terminal = GameState(
        state.position,
        state.ply_count,
        state.repetition_counts,
        TerminalResult(TerminalStatus.STALEMATE),
    )
    assert legal_successors(terminal, compiled) == ()


def test_fingerprint_mismatch_raises():
    compiled_a = build_4x4_rooks()
    compiled_b = build_mate(2)
    state = GameSession(compiled_a).state
    with pytest.raises(RuleSetMismatchError):
        legal_successors(state, compiled_b)


def test_legal_successors_include_drops():
    compiled = build_4x4_rooks()
    state = make_state(compiled, ["....", "....", "....", "K..k"], hands=([("R", 2)], ()))
    assert any(isinstance(action, DropMove) for action, _ in legal_successors(state, compiled))


def test_legal_successors_include_promotion_variants():
    compiled = build_promotion()
    lines = [
        ".......k",
        "....P...",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    state = make_state(compiled, lines, side_to_move=0)
    promoted = [
        action
        for action, _ in legal_successors(state, compiled)
        if isinstance(action, BoardMove) and action.promotion_target_id is not None
    ]
    assert promoted

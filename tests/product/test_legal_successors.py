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


@pytest.mark.parametrize("fixture_name", ["cannon", "castling", "en_passant", "nifu", "uchifuzume"])
def test_semantic_successors_preserve_complete_state_through_actual_history(fixture_name):
    import rule_semantics_ir_fixtures as fixtures
    from generic_chess.rules.compiler import compile_ruleset_for_execution

    compiled = compile_ruleset_for_execution(getattr(fixtures, fixture_name + "_ruleset")())
    session = GameSession(compiled)
    for _ in range(4):
        pairs = legal_successors(session.state, compiled)
        assert [a for a, _ in pairs] == legal_actions(session.state, compiled)
        for action, child in pairs:
            # Includes aux, hands, current/base/promoted identity, repetition,
            # check-event/action history and terminal adjudication, not just board.
            assert child == apply_action(session.state, action, compiled)
        if not pairs:
            break
        session.submit(pairs[0][0])


def test_semantic_eager_successors_do_not_reenumerate_parent_for_each_child(monkeypatch):
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.core.semantic_executor import SemanticEngine
    from rule_semantics_ir_fixtures import cannon_ruleset

    compiled = compile_ruleset_for_execution(cannon_ruleset())
    state = GameSession(compiled).state
    original = SemanticEngine.iter_legal_action_bindings
    parent_enumerations = []

    def observed(self, position, checkpoint=None):
        if position is state.position:
            parent_enumerations.append(position)
        yield from original(self, position, checkpoint=checkpoint)

    monkeypatch.setattr(SemanticEngine, "iter_legal_action_bindings", observed)
    pairs = legal_successors(state, compiled)
    assert len(pairs) > 1
    assert len(parent_enumerations) == 1


@pytest.mark.parametrize("target,winning_drops", [("G", 1), ("TP", 0)])
def test_semantic_successors_after_capture_preserve_drop_postconditions(target, winning_drops):
    from dataclasses import replace
    from generic_chess.core.pieces import Piece
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset

    board = [[None] * 9 for _ in range(9)]
    for owner, tid, file, rank in ((0, "K", 7, 6), (1, "K", 8, 8), (0, "N", 3, 2)):
        board[rank][file] = Piece(owner, tid, tid)
    board[4][4] = Piece(1, "P" if target == "TP" else "G", target, target == "TP")
    rules = replace(build_standard_shogi_ruleset(), initial_position=tuple(map(tuple, board)))
    compiled = compile_ruleset_for_execution(rules)
    session = GameSession(compiled)
    capture = next(a for a in session.legal_actions()
                   if a.to_square.file == 4 and a.to_square.rank == 4
                   and a.promotion_target_id is None)
    session.submit(capture)
    reply, = session.legal_actions()
    session.submit(reply)
    pairs = legal_successors(session.state, compiled)
    assert tuple(a for a, _ in pairs) == session.legal_actions()
    for action, child in pairs:
        assert child == apply_action(session.state, action, compiled)
    # Actual capture-reset hand G vs P: S4 filtering and terminal semantics
    # survive the binding reuse, including the pawn-drop-mate prohibition.
    wins = [(a, child) for a, child in pairs if hasattr(a, "base_type_id")
            and child.terminal_status.is_terminal and child.terminal_status.winner == 0]
    assert len(wins) == winning_drops

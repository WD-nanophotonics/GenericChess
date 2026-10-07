from dataclasses import replace

import pytest

from generic_chess.core.actions import (
    action_is_board,
    action_source_square,
    action_target_square,
)
from generic_chess.core.coordinates import Square
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalResult, TerminalStatus, terminal_result
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.native.compiler import NativeUnsupportedRuleError, compile_native_semantic_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleNoProgressDraw, compute_fingerprint
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.result import SessionStatus, session_result_from_terminal


def _compiled(pieces, *, semantic):
    rows = [[None] * 8 for _ in range(8)]
    for owner, type_id, square in pieces:
        rows[square.rank][square.file] = Piece(owner, type_id, type_id)
    base = build_western_chess_ruleset()
    rules = replace(
        base,
        initial_position=tuple(tuple(row) for row in rows),
        semantic_actions=base.semantic_actions if semantic else (),
        no_progress_draw=RuleNoProgressDraw(4, True, ("P",)),
    )
    return compile_ruleset_for_execution(rules)


def _play(state, compiled, source, target):
    action = next(
        item
        for item in legal_actions(state, compiled)
        if action_is_board(item)
        and action_source_square(item) == source
        and action_target_square(item) == target
    )
    return apply_action(state, action, compiled)


@pytest.mark.parametrize("semantic", (False, True))
def test_four_quiet_plies_draw_with_matching_immutable_and_semantic_terminals(semantic):
    compiled = _compiled(
        (
            (0, "K", Square(0, 0)),
            (1, "K", Square(7, 7)),
            (0, "N", Square(1, 0)),
            (1, "N", Square(6, 7)),
        ),
        semantic=semantic,
    )
    state = initial_state(compiled)
    assert state.terminal_status.status is TerminalStatus.ONGOING
    for source, target in (
        (Square(1, 0), Square(0, 2)),
        (Square(6, 7), Square(7, 5)),
        (Square(0, 2), Square(1, 0)),
        (Square(7, 5), Square(6, 7)),
    ):
        state = _play(state, compiled, source, target)
        if state.ply_count < 4:
            assert state.terminal_status.status is TerminalStatus.ONGOING
    assert state.terminal_status.status is TerminalStatus.NO_PROGRESS_DRAW
    assert terminal_result(state, compiled) == state.terminal_status
    assert session_result_from_terminal(state.terminal_status).status is SessionStatus.NO_PROGRESS_DRAW


def test_configured_mover_resets_the_counter_on_semantic_path():
    semantic = True
    pawn_compiled = _compiled(
        (
            (0, "K", Square(0, 0)),
            (1, "K", Square(0, 7)),
            (0, "P", Square(2, 2)),
        ),
        semantic=semantic,
    )
    state = _play(initial_state(pawn_compiled), pawn_compiled, Square(2, 2), Square(2, 3))
    assert state.terminal_status.status is TerminalStatus.ONGOING
    for source, target in (
        (Square(0, 7), Square(0, 6)),
        (Square(0, 0), Square(1, 0)),
        (Square(0, 6), Square(0, 7)),
        (Square(1, 0), Square(0, 0)),
    ):
        state = _play(state, pawn_compiled, source, target)
    assert state.terminal_status.status is TerminalStatus.NO_PROGRESS_DRAW


@pytest.mark.parametrize("semantic", (False, True))
def test_capture_by_any_piece_resets_the_counter(semantic):
    capture_compiled = _compiled(
        (
            (0, "K", Square(0, 0)),
            (1, "K", Square(0, 7)),
            (0, "R", Square(2, 2)),
            (1, "N", Square(2, 3)),
        ),
        semantic=semantic,
    )
    state = _play(initial_state(capture_compiled), capture_compiled, Square(2, 2), Square(2, 3))
    for source, target in (
        (Square(0, 7), Square(0, 6)),
        (Square(0, 0), Square(1, 0)),
        (Square(0, 6), Square(0, 7)),
    ):
        state = _play(state, capture_compiled, source, target)
    assert state.terminal_status.status is TerminalStatus.ONGOING
    state = _play(state, capture_compiled, Square(1, 0), Square(0, 0))
    assert state.terminal_status.status is TerminalStatus.NO_PROGRESS_DRAW


@pytest.mark.parametrize("semantic", (False, True))
def test_threshold_requires_complete_authoritative_history(semantic):
    compiled = _compiled(
        (
            (0, "K", Square(0, 0)),
            (1, "K", Square(7, 7)),
            (0, "N", Square(1, 0)),
            (1, "N", Square(6, 7)),
        ),
        semantic=semantic,
    )
    state = initial_state(compiled)
    for source, target in (
        (Square(1, 0), Square(0, 2)),
        (Square(6, 7), Square(7, 5)),
        (Square(0, 2), Square(1, 0)),
        (Square(7, 5), Square(6, 7)),
    ):
        state = _play(state, compiled, source, target)
    incomplete = replace(state, history=state.history[:-1])
    with pytest.raises(ValueError, match="complete history"):
        terminal_result(incomplete, compiled)


@pytest.mark.parametrize(
    ("semantic", "checked", "expected"),
    (
        (False, True, TerminalStatus.CHECKMATE),
        (False, False, TerminalStatus.STALEMATE),
        (True, True, TerminalStatus.CHECKMATE),
        (True, False, TerminalStatus.STALEMATE),
    ),
)
def test_no_legal_action_precedes_no_progress_draw_at_threshold(
    monkeypatch, semantic, checked, expected
):
    compiled = _compiled(
        (
            (0, "K", Square(0, 0)),
            (1, "K", Square(7, 7)),
            (0, "N", Square(1, 0)),
            (1, "N", Square(6, 7)),
        ),
        semantic=semantic,
    )
    state = initial_state(compiled)
    for source, target in (
        (Square(1, 0), Square(0, 2)),
        (Square(6, 7), Square(7, 5)),
        (Square(0, 2), Square(1, 0)),
        (Square(7, 5), Square(6, 7)),
    ):
        state = _play(state, compiled, source, target)
    ongoing = replace(state, terminal_status=TerminalResult(TerminalStatus.ONGOING))
    if semantic:
        monkeypatch.setattr(
            "generic_chess.core.semantic_executor.SemanticEngine.has_legal_action",
            lambda *_args, **_kwargs: False,
        )
        monkeypatch.setattr(
            "generic_chess.core.semantic_executor.SemanticEngine.in_check",
            lambda *_args, **_kwargs: checked,
        )
    else:
        monkeypatch.setattr("generic_chess.core.terminal.has_legal_action", lambda *_: False)
        monkeypatch.setattr("generic_chess.core.terminal.is_in_check", lambda *_: checked)
    winner = 1 - state.position.side_to_move if expected is TerminalStatus.CHECKMATE else None
    assert terminal_result(ongoing, compiled) == TerminalResult(expected, winner)


def test_absent_policy_preserves_legacy_serialization_and_fingerprint():
    rules = build_western_chess_ruleset()
    assert "no_progress_draw" not in serialize_ruleset(rules)
    assert compile_ruleset_for_execution(rules).no_progress_draw is None
    opted_in = replace(
        rules,
        no_progress_draw=RuleNoProgressDraw(4, True, ("P",)),
    )
    restored = deserialize_ruleset(serialize_ruleset(opted_in))
    assert restored.no_progress_draw == opted_in.no_progress_draw
    assert compute_fingerprint(restored) == compute_fingerprint(opted_in)
    assert compute_fingerprint(restored) != compute_fingerprint(rules)


def test_opted_in_ruleset_fails_closed_before_search_and_native_execution():
    compiled = _compiled(
        ((0, "K", Square(0, 0)), (1, "K", Square(7, 7))), semantic=True
    )
    state = initial_state(compiled)
    with pytest.raises(NotImplementedError, match="path-state identity"):
        SearchPathRuntime(state, compiled)
    with pytest.raises(NativeUnsupportedRuleError, match="no-progress draw"):
        compile_native_semantic_rules(compiled)
    assert not compiled.ir.capabilities.native_executable

from dataclasses import replace

import pytest

from generic_chess.core.actions import action_is_board, action_source_square, action_target_square
from generic_chess.core.coordinates import Square
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset

from no_progress_halfmove_test_support import extract_no_progress_halfmove_fact


RESET_TYPES = frozenset({"P"})


def _compiled(pieces, *, legacy=False):
    rows = [[None] * 8 for _ in range(8)]
    for owner, type_id, square in pieces:
        rows[square.rank][square.file] = Piece(owner, type_id, type_id)
    base = build_western_chess_ruleset()
    ruleset = replace(
        base,
        initial_position=tuple(tuple(row) for row in rows),
        semantic_actions=() if legacy else base.semantic_actions,
    )
    return compile_ruleset_for_execution(ruleset)


def _action(state, compiled, source, target, *, promotion=None):
    return next(
        action
        for action in legal_actions(state, compiled)
        if action_is_board(action)
        and action_source_square(action) == source
        and action_target_square(action) == target
        and action.promotion_target_id == promotion
    )


def _play(state, compiled, source, target, *, promotion=None):
    return apply_action(
        state,
        _action(state, compiled, source, target, promotion=promotion),
        compiled,
    )


def _king_pair():
    return ((0, "K", Square(0, 0)), (1, "K", Square(0, 7)))


@pytest.mark.parametrize(
    ("type_id", "source", "target"),
    (
        ("N", Square(2, 2), Square(3, 4)),
        ("B", Square(2, 2), Square(3, 3)),
        ("R", Square(2, 2), Square(2, 3)),
        ("K", Square(2, 2), Square(2, 3)),
    ),
)
def test_one_quiet_non_reset_piece_move_counts_one(type_id, source, target):
    pieces = (
        ((0, "K", source), (1, "K", Square(0, 7)))
        if type_id == "K"
        else (*_king_pair(), (0, type_id, source))
    )
    compiled = _compiled(pieces)
    state = _play(initial_state(compiled), compiled, source, target)

    fact = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )

    assert fact.status == "verified"
    assert fact.count == 1
    assert fact.reset_reasons == ()


def test_zero_plies_and_several_quiet_non_pawn_moves():
    compiled = _compiled(
        (
            *_king_pair(),
            (0, "N", Square(1, 0)),
            (1, "N", Square(6, 7)),
        )
    )
    state = initial_state(compiled)
    initial_fact = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )
    assert (initial_fact.status, initial_fact.count) == ("verified", 0)
    assert initial_fact.reset_reasons == ("initial",)

    for source, target in (
        (Square(1, 0), Square(0, 2)),
        (Square(6, 7), Square(7, 5)),
        (Square(0, 2), Square(1, 0)),
        (Square(7, 5), Square(6, 7)),
    ):
        state = _play(state, compiled, source, target)
    fact = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )

    assert fact.status == "verified"
    assert fact.count == 4


def test_pawn_move_resets_and_next_quiet_move_restarts_at_one():
    compiled = _compiled(
        (
            *_king_pair(),
            (0, "P", Square(2, 2)),
            (0, "N", Square(1, 0)),
        )
    )
    state = _play(initial_state(compiled), compiled, Square(2, 2), Square(2, 3))
    reset = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )
    assert (reset.status, reset.count, reset.reset_reasons) == (
        "verified", 0, ("mover_type:P",)
    )

    state = _play(state, compiled, Square(0, 7), Square(0, 6))
    restarted = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )
    assert (restarted.status, restarted.count, restarted.reset_reasons) == (
        "verified", 1, ()
    )


def test_rook_capture_resets_and_next_quiet_move_restarts_at_one():
    compiled = _compiled(
        (
            *_king_pair(),
            (0, "R", Square(2, 2)),
            (1, "N", Square(2, 3)),
        )
    )
    state = _play(initial_state(compiled), compiled, Square(2, 2), Square(2, 3))
    reset = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )
    assert (reset.status, reset.count, reset.reset_reasons) == (
        "verified", 0, ("capture",)
    )

    state = _play(state, compiled, Square(0, 7), Square(0, 6))
    restarted = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )
    assert (restarted.status, restarted.count) == ("verified", 1)


def test_pawn_capture_reports_both_independent_reset_reasons():
    compiled = _compiled(
        (
            *_king_pair(),
            (0, "P", Square(2, 2)),
            (1, "N", Square(3, 3)),
        )
    )
    state = _play(initial_state(compiled), compiled, Square(2, 2), Square(3, 3))

    fact = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )

    assert (fact.status, fact.count) == ("verified", 0)
    assert fact.reset_reasons == ("capture", "mover_type:P")


def test_short_replayed_history_covers_quiet_pawn_and_capture_resets():
    compiled = _compiled(
        (
            (0, "K", Square(0, 0)),
            (1, "K", Square(7, 7)),
            (0, "R", Square(2, 2)),
            (0, "P", Square(0, 1)),
            (0, "N", Square(6, 0)),
            (1, "B", Square(2, 3)),
        )
    )
    state = initial_state(compiled)
    line = (
        (Square(2, 2), Square(2, 1), None),  # quiet rook: 1
        (Square(7, 7), Square(7, 6), None),  # quiet king: 2
        (Square(0, 1), Square(0, 2), None),  # Pawn move: 0
        (Square(7, 6), Square(7, 7), None),  # restart: 1
        (Square(6, 0), Square(5, 2), None),  # quiet knight: 2
        (Square(7, 7), Square(7, 6), None),  # quiet king: 3
        (Square(2, 1), Square(2, 3), None),  # rook capture: 0
        (Square(7, 6), Square(7, 7), None),  # restart: 1
    )
    observed = []
    for source, target, promotion in line:
        state = _play(state, compiled, source, target, promotion=promotion)
        fact = extract_no_progress_halfmove_fact(
            state, compiled, reset_type_ids=RESET_TYPES
        )
        assert fact.status == "verified", fact.reason
        observed.append(fact.count)

    assert observed == [1, 2, 0, 1, 2, 3, 0, 1]


def test_promotion_move_resets_by_pre_move_current_type():
    compiled = _compiled(
        (
            (0, "K", Square(0, 0)),
            (1, "K", Square(0, 7)),
            (0, "P", Square(6, 6)),
        )
    )
    state = _play(
        initial_state(compiled), compiled,
        Square(6, 6), Square(6, 7), promotion="Q",
    )

    fact = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )

    assert (fact.status, fact.count, fact.reset_reasons) == (
        "verified", 0, ("mover_type:P",)
    )

    state = _play(state, compiled, Square(0, 7), Square(0, 6))
    promoted_piece_followup = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )
    assert (promoted_piece_followup.status, promoted_piece_followup.count) == (
        "verified", 1
    )


def test_castling_is_a_quiet_non_reset_board_move():
    compiled = _compiled(
        (
            (0, "K", Square(4, 0)),
            (0, "R", Square(7, 0)),
            (1, "K", Square(0, 7)),
        )
    )
    state = initial_state(compiled)
    castle = next(
        action for action in legal_actions(state, compiled)
        if action_is_board(action)
        and action_source_square(action) == Square(4, 0)
        and action_target_square(action) == Square(6, 0)
    )
    state = apply_action(state, castle, compiled)

    fact = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )

    assert (fact.status, fact.count, fact.reset_reasons) == (
        "verified", 1, ()
    )


def test_legacy_board_action_uses_pre_action_piece_not_action_actor_field():
    compiled = _compiled(
        (*_king_pair(), (0, "N", Square(1, 0))), legacy=True
    )
    state = _play(initial_state(compiled), compiled, Square(1, 0), Square(0, 2))
    action_kind = state.history[-1].action_signature
    assert '"kind":"board"' in action_kind

    fact = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )

    assert (fact.status, fact.count) == ("verified", 1)


def test_legacy_capture_uses_authoritative_inventory_delta():
    compiled = _compiled(
        (*_king_pair(), (0, "R", Square(2, 2)), (1, "N", Square(2, 3))),
        legacy=True,
    )
    state = _play(initial_state(compiled), compiled, Square(2, 2), Square(2, 3))
    assert '"kind":"board"' in state.history[-1].action_signature

    fact = extract_no_progress_halfmove_fact(
        state, compiled, reset_type_ids=RESET_TYPES
    )

    assert (fact.status, fact.count, fact.reset_reasons) == (
        "verified", 0, ("capture",)
    )


def test_incomplete_history_returns_unknown():
    compiled = _compiled((*_king_pair(), (0, "N", Square(1, 0))))
    state = _play(initial_state(compiled), compiled, Square(1, 0), Square(0, 2))
    truncated = replace(state, history=state.history[:-1])

    fact = extract_no_progress_halfmove_fact(
        truncated, compiled, reset_type_ids=RESET_TYPES
    )

    assert fact.status == "unknown"
    assert fact.count is None
    assert "every completed ply" in fact.reason

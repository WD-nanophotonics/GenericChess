from dataclasses import replace

from ai_fixtures import rook as rook_type
from conftest import king_type

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.history_recapture_trace import (
    trace_history_immediate_recaptures,
)
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleSet


def _compiled_ruleset(*, pinned):
    rows = [[None] * 5 for _ in range(5)]
    pieces = (
        (Square(1, 0), Piece(0, "K", "K")),
        (Square(4, 4), Piece(1, "K", "K")),
        (Square(0, 0), Piece(0, "R", "R")),  # quiet first move
        (Square(1, 1), Piece(0, "R", "R")),  # possible recapturer
        (Square(3, 1), Piece(0, "R", "R")),  # captured piece
        (Square(3, 3), Piece(1, "R", "R")),  # capturing piece
    )
    for square, piece in pieces:
        rows[square.rank][square.file] = piece
    if pinned:
        rows[4][1] = Piece(1, "R", "R")  # pins the recapturer to its King
    mask = (True,) * 25
    ruleset = RuleSet(
        board_size=5,
        piece_types=(king_type(), rook_type()),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"R": (mask, mask)},
        promotion_allowed={},
        promotion_forced={},
    )
    return compile_ruleset_for_execution(ruleset)


def _legal_move(state, compiled, source, target):
    matches = tuple(
        action
        for action in legal_actions(state, compiled)
        if isinstance(action, BoardMove)
        and action.from_square == source
        and action.to_square == target
    )
    assert len(matches) == 1, (source, target, matches)
    return matches[0]


def _captured_state(*, pinned):
    compiled = _compiled_ruleset(pinned=pinned)
    state = initial_state(compiled)
    quiet = _legal_move(state, compiled, Square(0, 0), Square(0, 1))
    state = apply_action(state, quiet, compiled)
    capture = _legal_move(state, compiled, Square(3, 3), Square(3, 1))
    state = apply_action(state, capture, compiled)
    return state, compiled


def test_history_immediate_recapture_maps_pinned_and_unpinned_witness_tokens():
    observations = []
    for pinned in (False, True):
        state, compiled = _captured_state(pinned=pinned)
        provenance = reconstruct_history_provenance(state, compiled)
        assert provenance.status == "verified", provenance.reason
        trace = trace_history_immediate_recaptures(state, compiled)
        assert trace.status == "verified", trace.reason
        assert len(trace.facts) == 1

        fact = trace.facts[0]
        before = provenance.frames[fact.capture_ply - 1]
        assert fact.capture_ply == 2
        assert fact.actor == 1
        assert fact.capture_source == Square(3, 3)
        assert fact.capture_target == Square(3, 1)
        assert fact.capturer_token == before.identities[
            square_to_index(fact.capture_source, before.position.board_shape)
        ]
        assert fact.captured_token == before.identities[
            square_to_index(fact.capture_target, before.position.board_shape)
        ]
        if pinned:
            assert fact.recapturer_sources == ()
            assert fact.recapturer_tokens == ()
        else:
            assert fact.recapturer_sources == (Square(1, 1),)
            assert len(fact.recapturer_tokens) == 1
            assert fact.recapturer_tokens[0] == before.identities[
                square_to_index(Square(1, 1), before.position.board_shape)
            ]
        observations.append(fact)

    assert observations[0].capture_source == observations[1].capture_source
    assert observations[0].capture_target == observations[1].capture_target
    assert observations[0].capturer_token == observations[1].capturer_token
    assert observations[0].captured_token == observations[1].captured_token
    assert observations[0].recapturer_tokens
    assert not observations[1].recapturer_tokens


def test_history_immediate_recapture_trace_fails_closed_on_truncated_history():
    state, compiled = _captured_state(pinned=False)
    incomplete = replace(state, history=state.history[1:])
    trace = trace_history_immediate_recaptures(incomplete, compiled)
    assert trace.status == "unknown"
    assert trace.facts == ()
    assert trace.reason

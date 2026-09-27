from dataclasses import replace

from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.capture_pressure_trace import (
    trace_capture_pressure,
    trace_next_turn_legal_captures,
)
from generic_chess.core.capture_sources import (
    query_capture_sources,
    query_counterfactual_legal_capture_sources,
)
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset


def _compiled_with(pieces):
    rows = [[None] * 9 for _ in range(10)]
    for square, piece in pieces:
        rows[square.rank][square.file] = piece
    ruleset = replace(
        build_xiangqi_diagnostic_ruleset(),
        initial_position=tuple(tuple(row) for row in rows),
    )
    return compile_ruleset_for_execution(ruleset)


def _play(state, compiled, source, target):
    matches = [
        action for action in legal_actions(state, compiled)
        if isinstance(action, SemanticBoardMove)
        and action.from_square == source
        and action.to_square == target
    ]
    assert len(matches) == 1, (source, target, matches)
    return apply_action(state, matches[0], compiled)


def _base_pieces(*, chariot=Square(0, 8), target=Square(0, 4)):
    return (
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(3, 9), Piece(1, "G", "G")),
        (chariot, Piece(0, "R", "R")),
        (target, Piece(1, "S", "S")),
    )


def _one_ply_facts(state, compiled):
    provenance = reconstruct_history_provenance(state, compiled)
    assert provenance.status == "verified", provenance.reason
    pressure = trace_capture_pressure(state, compiled)
    assert pressure.status == "verified", pressure.reason
    legal = trace_next_turn_legal_captures(state, compiled)
    assert legal.status == "verified", legal.reason
    action_sources = {
        fact.action_source_token
        for fact in pressure.facts
        if fact.ply == 1 and fact.action_source_token is not None
    }
    assert len(action_sources) == 1, action_sources
    return provenance, pressure, legal, next(iter(action_sources))


def _identity(frame, square):
    return frame.identities[
        square_to_index(square, frame.position.board_shape)
    ]


def test_moved_chariot_token_joins_its_post_move_legal_capture_edge():
    source, destination, target = Square(0, 8), Square(1, 8), Square(1, 4)
    compiled = _compiled_with(_base_pieces(target=target))
    state = _play(initial_state(compiled), compiled, source, destination)

    provenance, pressure, legal, action_source_token = _one_ply_facts(
        state, compiled
    )
    before, after = provenance.frames
    chariot_token = _identity(before, source)
    target_token = _identity(after, target)
    assert chariot_token is not None and target_token is not None
    assert _identity(after, destination) == chariot_token
    assert action_source_token == chariot_token

    joined = tuple(
        edge for edge in legal.facts
        if edge.frame_ply == 1
        and edge.source_token == action_source_token
        and edge.target_token == target_token
    )
    assert len(joined) == 1
    assert joined[0].source == destination and joined[0].target == target
    assert joined[0].actor == 0 and joined[0].side_to_move == 1
    post_as_mover = replace(state, position=replace(after.position, side_to_move=0))
    assert any(
        isinstance(action, SemanticBoardMove)
        and action.from_square == destination
        and action.to_square == target
        for action in legal_actions(post_as_mover, compiled)
    )
    assert any(
        fact.ply == 1
        and fact.action_source_token == chariot_token
        and fact.source_token == chariot_token
        and fact.target_token == target_token
        and fact.pseudo_capture_after
        for fact in pressure.facts
    )


def test_unrelated_general_move_does_not_claim_an_existing_chariot_threat():
    general_source, general_target = Square(4, 0), Square(4, 1)
    chariot, soldier = Square(0, 8), Square(0, 4)
    compiled = _compiled_with(_base_pieces(chariot=chariot, target=soldier))
    state = _play(
        initial_state(compiled), compiled, general_source, general_target
    )

    provenance, pressure, legal, action_source_token = _one_ply_facts(
        state, compiled
    )
    before, after = provenance.frames
    general_token = _identity(before, general_source)
    chariot_token = _identity(after, chariot)
    target_token = _identity(after, soldier)
    assert general_token is not None and chariot_token is not None
    assert target_token is not None
    assert _identity(after, general_target) == general_token
    assert action_source_token == general_token
    assert chariot_token != action_source_token

    # The same legal edge remains in the position, but it did not come from
    # the just-completed action's source token.
    assert any(
        edge.frame_ply == 1
        and edge.source_token == chariot_token
        and edge.target_token == target_token
        for edge in legal.facts
    )
    assert not any(
        edge.frame_ply == 1
        and edge.source_token == action_source_token
        and edge.target_token == target_token
        for edge in legal.facts
    )
    assert any(
        fact.ply == 1
        and fact.action_source_token == general_token
        and fact.source_token == chariot_token
        and fact.target_token == target_token
        and fact.pseudo_capture_after
        for fact in pressure.facts
    )


def test_pinned_chariot_pseudo_edge_is_not_a_moved_piece_legal_capture_fact():
    pinned, target = Square(4, 1), Square(5, 1)
    mover_source, mover_destination = Square(0, 8), Square(1, 8)
    pieces = (
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(3, 9), Piece(1, "G", "G")),
        (pinned, Piece(0, "R", "R")),
        (mover_source, Piece(0, "R", "R")),
        (Square(4, 8), Piece(1, "R", "R")),
        (target, Piece(1, "S", "S")),
    )
    compiled = _compiled_with(pieces)
    state = _play(
        initial_state(compiled), compiled, mover_source, mover_destination
    )

    provenance, pressure, legal, action_source_token = _one_ply_facts(
        state, compiled
    )
    after = provenance.frames[1]
    pinned_token = _identity(after, pinned)
    target_token = _identity(after, target)
    assert pinned_token is not None and target_token is not None
    assert action_source_token == _identity(provenance.frames[0], mover_source)
    assert action_source_token != pinned_token

    pseudo = query_capture_sources(after.position, target, 0, compiled)
    assert pinned in pseudo.pseudo_capture_sources
    assert pseudo.legal_capture_sources is None  # actual side to move is owner 1
    counterfactual_sources = query_counterfactual_legal_capture_sources(
        after.position, target, 0, compiled
    )
    assert counterfactual_sources == ()
    assert not any(
        edge.frame_ply == 1
        and edge.source_token == pinned_token
        and edge.target_token == target_token
        for edge in legal.facts
    )
    assert any(
        fact.ply == 1
        and fact.action_source_token == action_source_token
        and fact.source_token == pinned_token
        and fact.target_token == target_token
        and fact.pseudo_capture_after
        for fact in pressure.facts
    )

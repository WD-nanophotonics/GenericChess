from dataclasses import replace

from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.capture_pressure_trace import trace_capture_pressure
from generic_chess.core.capture_sources import query_capture_sources
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset


def _minimal_xiangqi_identity_ruleset():
    rows = [[None] * 9 for _ in range(10)]
    pieces = (
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(3, 9), Piece(1, "G", "G")),
        (Square(0, 8), Piece(0, "R", "R")),
        (Square(0, 4), Piece(1, "S", "S")),
        (Square(1, 4), Piece(1, "S", "S")),
    )
    for square, piece in pieces:
        rows[square.rank][square.file] = piece

    return replace(
        build_xiangqi_diagnostic_ruleset(),
        initial_position=tuple(tuple(row) for row in rows),
    )


def _apply_public_legal_move(state, compiled, source, target):
    candidates = [
        action
        for action in legal_actions(state, compiled)
        if isinstance(action, SemanticBoardMove)
        and action.from_square == source
        and action.to_square == target
    ]
    assert len(candidates) == 1, (source, target, candidates)
    return apply_action(state, candidates[0], compiled)


def _index(square, shape):
    return square_to_index(square, shape)


def test_xiangqi_legal_replay_distinguishes_same_square_same_type_target_instances():
    compiled = compile_ruleset_for_execution(_minimal_xiangqi_identity_ruleset())
    initial = initial_state(compiled)
    state = initial
    moves = (
        (Square(4, 0), Square(4, 1)),
        (Square(0, 4), Square(0, 3)),
        (Square(4, 1), Square(4, 0)),
        (Square(1, 4), Square(0, 4)),
    )
    for source, target in moves:
        state = _apply_public_legal_move(state, compiled, source, target)

    provenance = reconstruct_history_provenance(state, compiled)
    assert provenance.status == "verified", provenance.reason
    assert len(provenance.frames) == 5
    frames = provenance.frames

    attacker_square = Square(0, 8)
    target_square = Square(0, 4)
    vacated_square = Square(0, 3)
    other_target_start = Square(1, 4)
    shape = compiled.board_shape
    attacker_index = _index(attacker_square, shape)
    target_index = _index(target_square, shape)
    vacated_index = _index(vacated_square, shape)
    other_target_index = _index(other_target_start, shape)

    attacker_ids = tuple(frame.identities[attacker_index] for frame in frames)
    assert attacker_ids[0] is not None
    assert all(token == attacker_ids[0] for token in attacker_ids)

    target_a_id = frames[0].identities[target_index]
    target_b_id = frames[0].identities[other_target_index]
    assert target_a_id is not None and target_b_id is not None
    assert target_a_id != target_b_id
    assert frames[0].identities[target_index] == target_a_id
    assert frames[2].identities[vacated_index] == target_a_id
    assert frames[4].identities[vacated_index] == target_a_id
    assert frames[4].identities[target_index] == target_b_id

    initial_target = frames[0].position.board[target_index]
    final_target = frames[4].position.board[target_index]
    assert initial_target is not None and final_target is not None
    assert (initial_target.owner, initial_target.base_type_id) == (1, "S")
    assert (final_target.owner, final_target.base_type_id) == (1, "S")
    assert initial_target.base_type_id == final_target.base_type_id

    # Source-specific capture facts agree exactly with the public legal-action
    # authority at both endpoints of the replay.
    for frame_number, live_state, target_token in (
        (0, initial, target_a_id),
        (4, state, target_b_id),
    ):
        frame = frames[frame_number]
        assert frame.identities[target_index] == target_token
        evidence = query_capture_sources(
            frame.position, target_square, 0, compiled
        )
        assert attacker_square in evidence.pseudo_attack_sources
        assert attacker_square in evidence.pseudo_capture_sources
        assert evidence.legal_capture_sources is not None
        assert attacker_square in evidence.legal_capture_sources

        public_sources = {
            action.from_square
            for action in legal_actions(live_state, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.to_square == target_square
        }
        assert set(evidence.legal_capture_sources) == public_sources
        assert public_sources == {attacker_square}

    # A type-and-square-only identity heuristic would merge these targets;
    # replay provenance correctly does not.
    initial_type_square = (initial_target.base_type_id, target_square)
    final_type_square = (final_target.base_type_id, target_square)
    assert initial_type_square == final_type_square
    assert frames[0].identities[target_index] != frames[4].identities[target_index]

    trace = trace_capture_pressure(state, compiled)
    assert trace.status == "verified", trace.reason
    target_a_move = next(
        fact
        for fact in trace.facts
        if fact.ply == 2
        and fact.source_token == attacker_ids[0]
        and fact.target_token == target_a_id
    )
    assert target_a_move.pseudo_capture_before
    assert target_a_move.pseudo_capture_after
    assert target_a_move.target_transition == "moved"
    assert target_a_move.before_target == target_square
    assert target_a_move.after_target == vacated_square

    target_b_reoccupation = next(
        fact
        for fact in trace.facts
        if fact.ply == 4
        and fact.source_token == attacker_ids[0]
        and fact.target_token == target_b_id
    )
    assert not target_b_reoccupation.pseudo_capture_before
    assert target_b_reoccupation.pseudo_capture_after
    assert target_b_reoccupation.target_transition == "moved"
    assert target_b_reoccupation.before_target == other_target_start
    assert target_b_reoccupation.after_target == target_square

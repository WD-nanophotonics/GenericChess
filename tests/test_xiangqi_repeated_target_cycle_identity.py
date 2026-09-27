from dataclasses import replace

from generic_chess.core.actions import SemanticBoardMove
from history_candidate_test_support import (
    extract_repeated_cycle_capture_candidate,
)
from generic_chess.core.capture_pressure_trace import trace_next_turn_legal_captures
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.history_cycle_trace import (
    trace_latest_repeated_cycle_capture_facts,
)
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset


def _compiled_cycle_ruleset():
    rows = [[None] * 9 for _ in range(10)]
    for square, piece in (
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(5, 9), Piece(1, "G", "G")),
        (Square(0, 5), Piece(1, "R", "R")),  # recurring chaser
        (Square(3, 5), Piece(0, "R", "R")),  # target A
        (Square(4, 5), Piece(0, "R", "R")),  # same-type target B
    ):
        rows[square.rank][square.file] = piece
    ruleset = replace(
        build_xiangqi_diagnostic_ruleset(),
        initial_position=tuple(tuple(row) for row in rows),
    )
    return compile_ruleset_for_execution(ruleset)


def _replay(compiled, moves, expected_occurrences=2):
    state = initial_state(compiled)
    initial_key = position_identity_key(state.position, compiled)
    for source, target in moves:
        action = next(
            candidate for candidate in legal_actions(state, compiled)
            if isinstance(candidate, SemanticBoardMove)
            and candidate.from_square == source
            and candidate.to_square == target
        )
        state = apply_action(state, action, compiled)
    assert position_identity_key(state.position, compiled) == initial_key
    assert dict(state.repetition_counts)[str(initial_key)] == expected_occurrences
    provenance = reconstruct_history_provenance(state, compiled)
    assert provenance.status == "verified", provenance.reason
    trace = trace_next_turn_legal_captures(state, compiled)
    assert trace.status == "verified", trace.reason
    return state, initial_key, provenance, trace


def _chaser_edges(trace, provenance, frame_numbers):
    source = Square(0, 5)
    frames = provenance.frames
    source_index = square_to_index(source, frames[0].position.board_shape)
    chaser_id = frames[0].identities[source_index]
    assert chaser_id is not None
    edges = []
    for frame_number in frame_numbers:
        fact = next(
            item for item in trace.facts
            if item.frame_ply == frame_number
            and item.source_token == chaser_id
        )
        edges.append(fact)
    return chaser_id, tuple(edges)


def test_repeated_xiangqi_cycle_distinguishes_same_target_from_same_square_substitution():
    compiled = _compiled_cycle_ruleset()
    target = Square(3, 5)

    same_target_moves = (
        (Square(3, 5), Square(3, 4)),  # target A steps off the rank
        (Square(0, 5), Square(0, 4)),  # chaser threatens A on the new rank
        (Square(3, 4), Square(3, 5)),  # A returns to the target square
        (Square(0, 4), Square(0, 5)),  # chaser threatens the same A again
    )
    same_state, same_key, same_provenance, same_trace = _replay(
        compiled, same_target_moves * 2, expected_occurrences=3
    )
    same_chaser, same_edges = _chaser_edges(
        same_trace, same_provenance, (6, 8)
    )
    same_cycle = trace_latest_repeated_cycle_capture_facts(same_state, compiled)
    assert same_cycle.status == "verified", same_cycle.reason
    assert same_cycle.cycle is not None
    assert (same_cycle.cycle.start_ply, same_cycle.cycle.end_ply) == (4, 8)
    same_cycle_edges = tuple(
        fact for fact in same_cycle.cycle.capture_facts
        if fact.source_token == same_chaser
    )
    assert tuple(fact.frame_ply for fact in same_cycle_edges) == (6, 8)
    assert tuple(fact.target_token for fact in same_cycle_edges) == tuple(
        edge.target_token for edge in same_edges
    )
    same_response = next(
        fact for fact in same_cycle.cycle.response_facts
        if fact.threat_frame_ply == 6
        and fact.source_token == same_chaser
    )
    assert same_response.response_ply == 7
    assert same_response.response_wrapped is False
    assert same_response.target_moved is True
    assert same_response.specific_capture_still_legal is False
    assert same_response.response_action_source_token == same_edges[0].target_token
    wrapped_same = next(
        fact for fact in same_cycle.cycle.response_facts
        if fact.threat_frame_ply == 8
        and fact.source_token == same_chaser
    )
    assert wrapped_same.response_ply == 5
    assert wrapped_same.response_wrapped is True
    assert wrapped_same.target_moved is True
    assert wrapped_same.specific_capture_still_legal is False
    same_initial_id = same_provenance.frames[0].identities[
        square_to_index(target, same_provenance.frames[0].position.board_shape)
    ]
    assert same_initial_id is not None
    assert tuple(edge.target_token for edge in same_edges) == (same_initial_id,) * 2
    assert tuple(edge.target for edge in same_edges) == (
        Square(3, 4), target
    )
    assert position_identity_key(same_state.position, compiled) == same_key
    candidate = extract_repeated_cycle_capture_candidate(
        same_cycle, same_chaser, same_initial_id
    )
    assert candidate.status == "candidate", candidate.reason
    assert (candidate.start_ply, candidate.end_ply) == (4, 8)
    assert tuple(step.frame_ply for step in candidate.evidence) == (6, 8)
    assert candidate.evidence[-1].response_facts[0].response_wrapped is True

    substituted_moves = (
        (Square(3, 5), Square(3, 4)),
        (Square(0, 5), Square(0, 4)),
        (Square(4, 5), Square(3, 5)),  # B takes the vacated square
        (Square(0, 4), Square(0, 5)),  # same chaser, same target square
        (Square(3, 5), Square(4, 5)),  # B returns
        (Square(0, 5), Square(0, 4)),
        (Square(3, 4), Square(3, 5)),  # A restores the initial occupancy
        (Square(0, 4), Square(0, 5)),
    )
    swap_state, swap_key, swap_provenance, swap_trace = _replay(
        compiled, substituted_moves
    )
    swap_chaser, swap_edges = _chaser_edges(
        swap_trace, swap_provenance, (2, 4, 6, 8)
    )
    swap_cycle = trace_latest_repeated_cycle_capture_facts(swap_state, compiled)
    assert swap_cycle.status == "verified", swap_cycle.reason
    assert swap_cycle.cycle is not None
    assert (swap_cycle.cycle.start_ply, swap_cycle.cycle.end_ply) == (0, 8)
    swap_cycle_edges = tuple(
        fact for fact in swap_cycle.cycle.capture_facts
        if fact.source_token == swap_chaser
    )
    assert tuple(fact.frame_ply for fact in swap_cycle_edges) == (2, 4, 6, 8)
    assert tuple(fact.target_token for fact in swap_cycle_edges) == tuple(
        edge.target_token for edge in swap_edges
    )
    initial_target_id = swap_provenance.frames[0].identities[
        square_to_index(target, swap_provenance.frames[0].position.board_shape)
    ]
    substituted_target_id = swap_provenance.frames[4].identities[
        square_to_index(target, swap_provenance.frames[4].position.board_shape)
    ]
    assert initial_target_id is not None and substituted_target_id is not None
    assert initial_target_id != substituted_target_id
    assert swap_provenance.frames[0].position.board[
        square_to_index(target, swap_provenance.frames[0].position.board_shape)
    ].base_type_id == swap_provenance.frames[4].position.board[
        square_to_index(target, swap_provenance.frames[4].position.board_shape)
    ].base_type_id == "R"
    assert tuple(edge.target_token for edge in swap_edges) == (
        initial_target_id, substituted_target_id,
        initial_target_id, initial_target_id,
    )
    assert swap_edges[1].target == target
    assert position_identity_key(swap_state.position, compiled) == swap_key == same_key

    substitution_response = next(
        fact for fact in swap_cycle.cycle.response_facts
        if fact.threat_frame_ply == 2
        and fact.source_token == swap_chaser
        and fact.target_token == initial_target_id
    )
    assert substitution_response.response_ply == 3
    assert substitution_response.target_moved is False
    assert substitution_response.specific_capture_still_legal is True
    assert substitution_response.response_action_source_token == substituted_target_id
    moved_target_response = next(
        fact for fact in swap_cycle.cycle.response_facts
        if fact.threat_frame_ply == 4
        and fact.source_token == swap_chaser
        and fact.target_token == substituted_target_id
    )
    assert moved_target_response.response_ply == 5
    assert moved_target_response.target_moved is True
    assert moved_target_response.specific_capture_still_legal is True
    replacement_candidate = extract_repeated_cycle_capture_candidate(
        swap_cycle, swap_chaser, initial_target_id
    )
    assert replacement_candidate.status == "not_candidate"
    assert (replacement_candidate.start_ply, replacement_candidate.end_ply) == (0, 8)
    assert tuple(step.frame_ply for step in replacement_candidate.evidence) == (
        2, 4, 6, 8
    )

    incomplete = replace(swap_state, history=swap_state.history[1:])
    unknown_cycle = trace_latest_repeated_cycle_capture_facts(incomplete, compiled)
    assert unknown_cycle.status == "unknown"
    assert unknown_cycle.cycle is None
    assert unknown_cycle.reason
    unknown_candidate = extract_repeated_cycle_capture_candidate(
        unknown_cycle, swap_chaser, initial_target_id
    )
    assert unknown_candidate.status == "unknown"

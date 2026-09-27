"""Minimal legal pair for repeated same-target capture-response facts.

These generic facts are not a WXF move-nature or outcome adjudicator.
"""

from dataclasses import replace

from generic_chess.core.actions import SemanticBoardMove
from history_candidate_test_support import (
    extract_repeated_cycle_capture_candidate,
)
from generic_chess.core.capture_pressure_trace import trace_next_turn_legal_captures
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.history_cycle_trace import (
    trace_latest_repeated_cycle_capture_facts,
)
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset


def _paired_trace(advisor_response):
    rows = [[None] * 9 for _ in range(10)]
    for square, piece in (
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(5, 7), Piece(1, "G", "G")),
        (Square(3, 9), Piece(0, "R", "R")),
        (Square(4, 8), Piece(1, "A", "A")),
    ):
        rows[square.rank][square.file] = piece

    ruleset = replace(
        build_xiangqi_diagnostic_ruleset(),
        initial_position=tuple(tuple(row) for row in rows),
    )
    compiled = compile_ruleset_for_execution(ruleset)
    # R threatens the Advisor, which either escapes (d8) or moves but remains
    # capturable (f10); R then returns, and the Advisor restores the position.
    moves = (
        (Square(3, 9), Square(4, 9)),
        (Square(4, 8), advisor_response),
        (Square(4, 9), Square(3, 9)),
        (advisor_response, Square(4, 8)),
    )
    state = initial_state(compiled)
    initial_key = position_identity_key(state.position, compiled)
    for _ in range(3):
        for source, target in moves:
            action = next(
                (
                    candidate
                    for candidate in legal_actions(state, compiled)
                    if isinstance(candidate, SemanticBoardMove)
                    and candidate.from_square == source
                    and candidate.to_square == target
                ),
                None,
            )
            assert action is not None, (source, target)
            state = apply_action(state, action, compiled)

    assert ruleset.repetition_limit == 4
    assert position_identity_key(state.position, compiled) == initial_key
    assert dict(state.repetition_counts)[str(initial_key)] == 4
    provenance = reconstruct_history_provenance(state, compiled)
    assert provenance.status == "verified", provenance.reason
    capture_trace = trace_next_turn_legal_captures(state, compiled)
    assert capture_trace.status == "verified", capture_trace.reason
    cycle_trace = trace_latest_repeated_cycle_capture_facts(state, compiled)
    assert cycle_trace.status == "verified", cycle_trace.reason
    assert cycle_trace.cycle is not None
    return provenance, cycle_trace


def test_same_target_pair_distinguishes_evading_from_still_legal_capture():
    # Exactly one Chariot chases one Advisor: neither 20.3 role exception
    # (King/Pawn chaser or un-crossed Pawn target) is part of this fixture.
    positive = _paired_trace(Square(3, 7))
    negative = _paired_trace(Square(5, 9))

    results = []
    for provenance, cycle_trace in (positive, negative):
        cycle = cycle_trace.cycle
        assert cycle is not None
        assert (cycle.start_ply, cycle.end_ply) == (0, 12)
        chaser = provenance.frames[0].identities[
            square_to_index(Square(3, 9), provenance.frames[0].position.board_shape)
        ]
        target = provenance.frames[0].identities[
            square_to_index(Square(4, 8), provenance.frames[0].position.board_shape)
        ]
        assert chaser is not None and target is not None
        edges = tuple(
            fact for fact in cycle.capture_facts if fact.source_token == chaser
        )
        assert tuple(fact.frame_ply for fact in edges) == (1, 3, 5, 7, 9, 11)
        assert all(fact.target_token == target for fact in edges)
        responses = tuple(
            fact
            for fact in cycle.response_facts
            if fact.source_token == chaser and fact.target_token == target
        )
        assert tuple(fact.response_ply for fact in responses) == (2, 4, 6, 8, 10, 12)
        assert all(fact.target_moved for fact in responses)
        candidate = extract_repeated_cycle_capture_candidate(
            cycle_trace, chaser, target
        )
        results.append(
            (
                candidate.status,
                tuple(fact.specific_capture_still_legal for fact in responses),
            )
        )

    assert results == [
        ("candidate", (False, False, False, False, False, False)),
        ("not_candidate", (True, False, True, False, True, False)),
    ]

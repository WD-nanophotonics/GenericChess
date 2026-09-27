"""Minimal facts and generic opt-in actor-loss rule for repeated-cycle targets."""

from dataclasses import replace
import json

import pytest

from generic_chess.core.actions import SemanticBoardMove, action_from_dict
from history_candidate_test_support import (
    extract_repeated_cycle_capture_candidate,
)
from generic_chess.core.capture_pressure_trace import trace_next_turn_legal_captures
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.history_cycle_trace import (
    evaluate_repeated_cycle_target_condition,
    summarize_repeated_cycle_targets,
    trace_latest_repeated_cycle_capture_facts,
)
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import (
    TerminalResult,
    TerminalStatus,
    _terminal_from_parts,
    terminal_from_search_runtime,
    terminal_result,
)
from generic_chess.core.adjudication import IncompleteAdjudicationHistoryError
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.session.result import SessionStatus, session_result_from_terminal
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.compiled import CompiledRepeatedCycleTargetCondition
from generic_chess.rules.schema import (
    RuleRepeatedCycleTargetCondition,
    ruleset_from_dict,
    ruleset_to_dict,
)
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
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


def _target_summary_trace(switch_targets, repeated_cycle_target_conditions=()):
    rows = [[None] * 9 for _ in range(10)]
    for square, piece in (
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(5, 7), Piece(1, "G", "G")),
        (Square(3, 9), Piece(0, "R", "R")),
        (Square(4, 8), Piece(1, "A", "A")),
        (Square(6, 8), Piece(1, "R", "R")),
    ):
        rows[square.rank][square.file] = piece

    ruleset = replace(
        build_xiangqi_diagnostic_ruleset(),
        initial_position=tuple(tuple(row) for row in rows),
        # The synthetic switch route has a shorter incidental repeat before
        # returning to its declared setup; keep the trace window non-terminal.
        repetition_limit=8,
        repeated_cycle_target_conditions=repeated_cycle_target_conditions,
    )
    ruleset = ruleset_from_dict(ruleset_to_dict(ruleset))
    compiled = compile_ruleset_for_execution(ruleset)
    replay_compiled = replace(
        compiled,
        ir=replace(compiled.ir, repeated_cycle_target_conditions=()),
    )
    if switch_targets:
        moves = (
            (Square(3, 9), Square(4, 9)),
            (Square(4, 8), Square(3, 7)),
            (Square(4, 9), Square(3, 9)),
            (Square(6, 8), Square(7, 8)),
            (Square(3, 9), Square(7, 9)),
            (Square(7, 8), Square(6, 8)),
            (Square(7, 9), Square(3, 9)),
            (Square(3, 7), Square(4, 8)),
        )
    else:
        moves = (
            (Square(3, 9), Square(4, 9)),
            (Square(4, 8), Square(3, 7)),
            (Square(4, 9), Square(3, 9)),
            (Square(3, 7), Square(4, 8)),
        )

    state = initial_state(replay_compiled)
    for _ in range(1 if repeated_cycle_target_conditions else 3):
        for source, target in moves:
            action = next(
                (
                    candidate
                    for candidate in legal_actions(state, replay_compiled)
                    if isinstance(candidate, SemanticBoardMove)
                    and candidate.from_square == source
                    and candidate.to_square == target
                ),
                None,
            )
            assert action is not None, (source, target)
            state = apply_action(state, action, replay_compiled)
    trace = trace_latest_repeated_cycle_capture_facts(state, replay_compiled)
    assert trace.status == "verified", trace.reason
    assert trace.cycle is not None
    return trace, state, compiled, ruleset


def test_repeated_cycle_target_projection_distinguishes_target_switch_on_same_setup():
    # The two histories share one declared starting board and piece inventory.
    # The control repeatedly exposes only the Advisor token; the variant also
    # exposes the second Chariot token during the cycle. This tests target-set
    # extraction, not whether either move sequence satisfies WXF chase rules.
    kept, kept_state, _, _ = _target_summary_trace(switch_targets=False)
    switched, switched_state, _, _ = _target_summary_trace(switch_targets=True)
    assert kept_state.position == switched_state.position
    kept_summary = summarize_repeated_cycle_targets(kept)
    switched_summary = summarize_repeated_cycle_targets(switched)
    assert kept_summary.status == switched_summary.status == "verified"

    def red_summary(summary):
        return next(actor for actor in summary.actors if actor.actor == 0)

    kept_red = red_summary(kept_summary)
    switched_red = red_summary(switched_summary)
    assert kept_red.distinct_target_count == 1
    assert kept_red.shared_target_count == 1
    assert kept_red.shared_target_tokens == kept_red.all_target_tokens
    assert switched_red.distinct_target_count == 2
    assert switched_red.shared_target_count == 0
    assert switched_red.shared_target_tokens == ()
    switched_token = next(
        token
        for token in switched_red.all_target_tokens
        if token not in kept_red.all_target_tokens
    )
    assert any(
        switched_token in targets
        for _ply, targets in switched_red.targets_by_ply
    )


def test_rule_cycle_target_condition_roundtrips_and_distinguishes_keep_from_switch():
    condition = RuleRepeatedCycleTargetCondition(actor=0)
    outcomes = []
    final_positions = []
    for switch_targets in (False, True):
        trace, state, compiled, ruleset = _target_summary_trace(
            switch_targets,
            repeated_cycle_target_conditions=(condition,),
        )
        serialized = ruleset_to_dict(ruleset)
        assert serialized["repeated_cycle_target_conditions"] == [
            {"actor": 0, "outcome": "actor_loss"}
        ]
        assert ruleset_from_dict(serialized) == ruleset
        assert compiled.repeated_cycle_target_conditions == (
            CompiledRepeatedCycleTargetCondition(actor=0),
        )
        assert compiled.ir.to_dict()["repeated_cycle_target_conditions"] == [
            {"actor": 0, "outcome": "actor_loss"}
        ]
        assert not compiled.ir.capabilities.native_executable
        summary = summarize_repeated_cycle_targets(trace)
        actor = compiled.repeated_cycle_target_conditions[0].actor
        outcomes.append(evaluate_repeated_cycle_target_condition(summary, actor))
        final_positions.append(state.position)

    assert final_positions[0] == final_positions[1]
    assert outcomes == ["satisfied", "unsatisfied"]


def test_cycle_target_condition_is_absent_from_chess_shogi_xiangqi_defaults():
    for builder in (
        build_western_chess_ruleset,
        build_standard_shogi_ruleset,
        build_xiangqi_diagnostic_ruleset,
    ):
        ruleset = builder()
        assert ruleset.repeated_cycle_target_conditions == ()
        assert "repeated_cycle_target_conditions" not in ruleset_to_dict(ruleset)
        compiled = compile_ruleset_for_execution(ruleset)
        assert compiled.repeated_cycle_target_conditions == ()
        state = initial_state(compiled)
        assert terminal_result(state, compiled) == state.terminal_status


def test_legacy_compiler_retains_opt_in_cycle_target_condition():
    ruleset = replace(
        build_western_chess_ruleset(),
        repeated_cycle_target_conditions=(RuleRepeatedCycleTargetCondition(actor=1),),
    )
    parsed = ruleset_from_dict(ruleset_to_dict(ruleset))
    compiled = compile_ruleset_for_execution(parsed)
    assert compiled.repeated_cycle_target_conditions == (
        CompiledRepeatedCycleTargetCondition(actor=1),
    )


def test_opt_in_cycle_target_outcome_disables_native_capability():
    base = build_western_chess_ruleset()
    baseline = compile_ruleset_for_execution(base)
    opted_in = compile_ruleset_for_execution(
        replace(
            base,
            repeated_cycle_target_conditions=(
                RuleRepeatedCycleTargetCondition(actor=0),
            ),
        )
    )
    assert baseline.ir.capabilities.native_executable
    assert not opted_in.ir.capabilities.native_executable


def test_actor_loss_is_identical_on_core_semantic_and_search_terminal_paths():
    for switch_targets, expected in (
        (False, TerminalResult(TerminalStatus.RULE_LOSS, winner=1)),
        (True, TerminalResult(TerminalStatus.ONGOING)),
    ):
        _trace, state, compiled, _ruleset = _target_summary_trace(
            switch_targets=switch_targets,
            repeated_cycle_target_conditions=(
                RuleRepeatedCycleTargetCondition(actor=0),
            ),
        )
        assert terminal_result(state, compiled) == expected
        assert _terminal_from_parts(
            state.position,
            state.ply_count,
            state.repetition_counts,
            compiled,
            state.history,
        ) == expected
        engine = semantic_engine_for(compiled)
        assert engine is not None
        assert engine.terminal_result(
            state.position,
            state.ply_count,
            state.repetition_counts,
            state.history,
        ) == expected
        assert session_result_from_terminal(expected).status is (
            SessionStatus.RULE_LOSS
            if expected.status is TerminalStatus.RULE_LOSS
            else SessionStatus.ONGOING
        )
        runtime = SearchPathRuntime.from_state(
            replace(state, terminal_status=expected), compiled
        )
        assert runtime._history_complete
        assert runtime.history_witness_misses == 0
        assert not runtime._opaque_imported_keys
        assert terminal_from_search_runtime(runtime) == expected
        if not switch_targets:
            prior = initial_state(compiled)
            for record in state.history[1:-1]:
                action = action_from_dict(json.loads(record.action_signature))
                prior = apply_action(prior, action, compiled)
            live_runtime = SearchPathRuntime.from_state(prior, compiled)
            final_action = action_from_dict(
                json.loads(state.history[-1].action_signature)
            )
            live_runtime.push(final_action)
            assert live_runtime.terminal_status == expected


def test_unsatisfied_and_unknown_cycle_conditions_never_award_actor_loss():
    _trace, state, compiled, _ruleset = _target_summary_trace(
        switch_targets=True,
        repeated_cycle_target_conditions=(RuleRepeatedCycleTargetCondition(actor=0),),
    )
    assert state.terminal_status == TerminalResult(TerminalStatus.ONGOING)

    incomplete = replace(
        state,
        history=(),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    with pytest.raises(IncompleteAdjudicationHistoryError, match="verifiable history"):
        terminal_result(incomplete, compiled)
    with pytest.raises(IncompleteAdjudicationHistoryError, match="verifiable history"):
        _terminal_from_parts(
            incomplete.position,
            incomplete.ply_count,
            incomplete.repetition_counts,
            compiled,
            incomplete.history,
        )
    runtime = SearchPathRuntime.from_state(incomplete, compiled)
    with pytest.raises(IncompleteAdjudicationHistoryError, match="trusted search history"):
        terminal_from_search_runtime(runtime)

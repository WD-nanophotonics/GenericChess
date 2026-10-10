"""Retained-result policy metadata, distinct from abort reason or horizon proof."""
from dataclasses import fields
import json

import pytest

from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.decision import PlayerDecision
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession
from scripts.research_record import record_value
from scripts.search_backend_comparison import CoreBoard


def position(setup='k4b2/6p1/8/8/8/6Q1/8/6K1 w - - 0 1'):
    compiled = compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    board = CoreBoard(dict(game='chess', setup=setup, moves=''), compiled)
    session = GameSession(compiled)
    session._state = board.initial
    session._search_history_witnesses = board.witnesses
    return session, board.material


def player(session, evaluator, *, tactical=False, use_tt=False):
    return AlphaBetaPlayer(session.compiled, evaluator_override=evaluator,
        use_native_semantic_legality=False, use_tt=use_tt,
        tuning=SearchTuning(use_root_tactical=tactical))


@pytest.mark.parametrize('q,depth,expected_q', [(0, 1, 0), (4, 1, 0), (4, 2, 4)])
def test_completed_iteration_captures_ordinary_policy_before_reserve_flag_changes(q, depth, expected_q):
    session, evaluator = position()
    before = session.state
    decision = player(session, evaluator).choose_action(session,
        SearchLimits(max_depth=depth, quiescence_max_depth=q,
                     quiescence_hard_max_depth=8))
    assert decision.completed_depth == depth
    assert decision.result_source == 'main_iteration'
    assert decision.result_ordinary_qdepth == expected_q
    assert decision.result_check_hard_qdepth == 8
    assert decision.action in session.legal_actions() and session.state == before
    encoded = record_value(decision)
    assert json.loads(json.dumps(encoded)) == encoded


@pytest.mark.parametrize('cancel_at_depth', [1, 2])
def test_cancel_after_completion_keeps_completed_policy_and_result(cancel_at_depth):
    session, evaluator = position()
    before = session.state
    token = CancellationToken()
    decision = player(session, evaluator).choose_action(session,
        SearchLimits(max_depth=3), cancel_token=token,
        progress_callback=lambda depth, *_: token.cancel() if depth == cancel_at_depth else None)
    assert decision.termination_reason == 'cancelled'
    assert decision.completed_depth == cancel_at_depth
    assert decision.result_source == 'main_iteration'
    assert decision.result_ordinary_qdepth == (0 if cancel_at_depth == 1 else 4)
    assert decision.result_check_hard_qdepth == 8
    assert session.state == before


@pytest.mark.parametrize('pre_cancelled', [False, True])
def test_legal_fallback_has_no_completed_q_policy(pre_cancelled):
    session, evaluator = position()
    token = CancellationToken()
    if pre_cancelled:
        token.cancel()
    decision = player(session, evaluator).choose_action(session,
        SearchLimits(max_nodes=None if pre_cancelled else 0), cancel_token=token)
    assert decision.termination_reason == ('cancelled' if pre_cancelled else 'node_limit')
    assert decision.completed_depth == 0 and decision.result_source == 'legal_fallback'
    assert decision.result_ordinary_qdepth is decision.result_check_hard_qdepth is None
    assert decision.action in session.legal_actions()


def test_partial_root_scan_keeps_scan_source_without_completion_claim():
    session, evaluator = position()
    decision = player(session, evaluator, tactical=True).choose_action(session,
        SearchLimits(max_nodes=1))
    assert decision.termination_reason == 'node_limit'
    assert decision.completed_depth == 0 and decision.result_source == 'root_scan_fallback'
    assert decision.result_ordinary_qdepth is decision.result_check_hard_qdepth is None


def test_immediate_mate_has_root_proof_source_without_iteration_policy():
    session, evaluator = position('k7/1Q6/2K5/8/8/8/8/8 w - - 0 1')
    decision = player(session, evaluator, tactical=True).choose_action(session, SearchLimits(max_depth=2))
    assert decision.termination_reason == 'root_immediate_win'
    assert decision.completed_depth == 0 and decision.result_source == 'root_immediate_win'
    assert decision.result_ordinary_qdepth is decision.result_check_hard_qdepth is None


def test_terminal_has_terminal_source_even_when_already_cancelled():
    session, evaluator = position('7k/6Q1/5K2/8/8/8/8/8 b - - 0 1')
    token = CancellationToken()
    token.cancel()
    decision = player(session, evaluator).choose_action(session, SearchLimits(), cancel_token=token)
    assert decision.action is None and decision.termination_reason == 'terminal_position'
    assert decision.result_source == 'terminal' and decision.completed_depth == 0
    assert decision.result_ordinary_qdepth is decision.result_check_hard_qdepth is None


def test_old_positional_decision_constructor_retains_unknown_provenance():
    session, evaluator = position()
    decision = player(session, evaluator).choose_action(session, SearchLimits(max_depth=1))
    legacy_fields = fields(PlayerDecision)[:-3]
    legacy = PlayerDecision(*(getattr(decision, field.name) for field in legacy_fields))
    assert legacy.action == decision.action and legacy.score == decision.score
    assert legacy.result_source == 'unknown'
    assert legacy.result_ordinary_qdepth is legacy.result_check_hard_qdepth is None


def test_warm_exact_return_policy_does_not_claim_cached_value_horizon():
    session, evaluator = position()
    engine = player(session, evaluator, use_tt=True)
    configured = engine.choose_action(session, SearchLimits(max_depth=2))
    reserve = engine.choose_action(session, SearchLimits(max_depth=1))
    assert configured.result_ordinary_qdepth == 4
    assert reserve.result_source == 'main_iteration'
    assert reserve.result_ordinary_qdepth == 0
    assert reserve.tt_hits > 0 and reserve.score == configured.score
    assert reserve.action == configured.action and reserve.completed_depth == 1

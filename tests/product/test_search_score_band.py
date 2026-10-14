"""Search heuristic totals cannot impersonate authoritative terminal utilities."""
from dataclasses import replace
import pytest

from ai_fixtures import build_4x4_rooks
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import (
    INF, _Budget, _Context, quiescence, reference_minimax,
)
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig, MATE_SCORE, MAX_STATIC_EVAL
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import terminal_result
from generic_chess.core.transition import apply_action
from generic_chess.session.session import GameSession
from scripts.chess_development import root_from_fen


def decide(session, evaluator, mdp=False):
    before = session.state, session.to_record(), session._search_witnesses
    decision = AlphaBetaPlayer(
        session.compiled, evaluator_override=evaluator, use_disk_cache=False,
        use_native_semantic_legality=False, use_tt=False, use_ordering=False,
        tuning=SearchTuning(use_mate_distance_pruning=mdp, use_root_tactical=False),
    ).choose_action(session, SearchLimits(max_depth=1, max_nodes=100000,
        max_time_seconds=5, quiescence_max_depth=0))
    assert before == (session.state, session.to_record(), session._search_witnesses)
    assert decision.completed_depth == 1 and decision.runtime_depth_balanced
    return decision


@pytest.mark.parametrize("scores", [
    (10, 20, 0),
    (MATE_SCORE+10, MATE_SCORE+20, 0),
    (-MATE_SCORE-20, -MATE_SCORE-10, -MATE_SCORE-100),
])
def test_mdp_and_plain_search_agree_on_bounded_override_utility(scores):
    session = GameSession(build_4x4_rooks())
    actions = sorted(session.legal_actions(), key=str)
    children = [apply_action(session.state, a, session.compiled) for a in actions]
    assert all(not x.terminal_status.is_terminal for x in children)
    values = [scores[0], scores[1]] + [scores[2]] * (len(actions)-2)

    class Evaluation:
        def evaluate(self, state):
            return -values[next(i for i, x in enumerate(children)
                                if x.position == state.position)]

    bounded = [max(-MAX_STATIC_EVAL, min(MAX_STATIC_EVAL, x)) for x in values]
    expected = actions[bounded.index(max(bounded))]
    plain, pruned = (decide(session, Evaluation(), mdp) for mdp in (False, True))
    reference, reference_action = reference_minimax(
        session.state, 1, Evaluation(), session.compiled)
    assert plain.action == pruned.action == reference_action == expected
    assert plain.score == pruned.score == reference == max(bounded)


@pytest.mark.parametrize("weight", [2, 1_000_000_000])
def test_actual_dynamic_evaluator_total_is_bounded_at_search_boundary(weight):
    session = GameSession(build_4x4_rooks())
    cfg = EvaluationConfig(dynamic_mobility_weight=weight,
                           anchor_escape_weight=0, promotion_potential_weight=0)
    evaluator = Evaluator(session.compiled,
        build_ruleset_profile(session.compiled, cfg), cfg)
    values = [-evaluator.evaluate(apply_action(session.state, a, session.compiled))
              for a in sorted(session.legal_actions(), key=str)]
    if weight > 2:
        assert max(abs(x) for x in values) > MATE_SCORE
    decisions = [decide(session, evaluator, mdp) for mdp in (False, True)]
    assert decisions[0].action == decisions[1].action
    assert all(d.score == max(max(-MAX_STATIC_EVAL, min(MAX_STATIC_EVAL, x))
                             for x in values) for d in decisions)


@pytest.mark.parametrize("mutable", [False, True])
@pytest.mark.parametrize("sign", [-1, 1])
def test_static_quiescence_leaf_uses_same_nonterminal_score_band(mutable, sign):
    session = GameSession(build_4x4_rooks())

    class Evaluation:
        def evaluate(self, state):
            return sign * 3 * MATE_SCORE

    limits = SearchLimits(quiescence_max_depth=0)
    runtime = SearchPathRuntime.from_state(session.state, session.compiled,
        history_witnesses=session._search_witnesses) if mutable else None
    ctx = _Context(session.compiled, Evaluation(), TranspositionTable(),
        SearchStatistics(), _Budget(limits, None), SearchTuning(),
        False, False, 0, 8, None, runtime=runtime)
    assert quiescence(session.state, -INF, INF, 0, 0, ctx) == sign * MAX_STATIC_EVAL
    if runtime is not None:
        runtime.assert_balanced()


@pytest.mark.parametrize("mdp", [False, True])
def test_real_terminal_win_dominates_oversized_nonterminal_evaluation(mdp):
    original = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    state = root_from_fen("k7/2K5/8/1Q6/8/8/8/8 w - - 0 1", original)
    compiled = compile_ruleset_for_execution(replace(
        build_builtin_ruleset("western_chess"), stalemate_result="loss"))
    position = replace(state.position, ruleset_fingerprint=compiled.ruleset_fingerprint)
    key = position_identity_key(position, compiled)
    state = replace(state, position=position, history=(HistoryRecord(key, -1, "", False),),
                    repetition_counts=((key, 1),))
    state = replace(state, terminal_status=terminal_result(state, compiled))
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = (position,)

    class Evaluation:
        def evaluate(self, state):
            return -3 * MATE_SCORE

    decision = decide(session, Evaluation(), mdp)
    child = apply_action(state, decision.action, compiled)
    assert child.terminal_status.is_terminal and child.terminal_status.winner == 0
    assert decision.score == MATE_SCORE-1


def test_real_mdp_cutoffs_retain_independent_three_ply_drop_goal():
    from conftest import make_state
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    state = make_state(compiled, ["....", "R...", "....", "K.k."],
                       hands=([("R", 1)], ()))
    session._state = state
    session._search_history_witnesses = (state.position,)
    before = session.state, session.to_record(), session._search_witnesses
    decisions = []
    for mdp in (False, True):
        decision = AlphaBetaPlayer(compiled, use_disk_cache=False,
            use_native_semantic_legality=False,
            tuning=SearchTuning(use_mate_distance_pruning=mdp)).choose_action(
                session, SearchLimits(max_depth=4, max_nodes=100000,
                    max_time_seconds=5, quiescence_max_depth=2))
        assert decision.completed_depth == 4
        assert decision.score == MATE_SCORE-3
        first = apply_action(state, decision.action, compiled)
        from generic_chess.core.movegen import legal_actions
        defenses = legal_actions(first, compiled)
        assert defenses
        for defense in defenses:
            second = apply_action(first, defense, compiled)
            assert any(apply_action(second, reply, compiled).terminal_status.winner == 0
                       for reply in legal_actions(second, compiled))
        assert before == (session.state, session.to_record(), session._search_witnesses)
        assert decision.runtime_depth_balanced
        decisions.append(decision)
    assert decisions[0].mate_pruning_cutoffs == 0
    assert decisions[1].mate_pruning_cutoffs > 0

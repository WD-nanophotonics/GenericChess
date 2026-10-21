"""Mixed ordering retains actual quiet/checking support and hard abort semantics."""
from dataclasses import replace
import pytest
from ai_fixtures import build_4x4_rooks
from conftest import make_state
from test_qsearch_correctness import _ctx, _evaluator, _king_rook_6, _check_chain_state
from test_qsearch_semantic_effects import transform_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.alphabeta.search import INF, SearchAborted, quiescence
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits


def context(c, state, evaluator, mutable, evasion_order, hard=8):
    ctx = _ctx(c, evaluator, SearchLimits(max_nodes=20000,
        quiescence_max_depth=4, quiescence_hard_max_depth=hard))
    ctx.tuning = SearchTuning(use_ordered_qsearch=True,
                              use_ordered_qsearch_in_check=evasion_order)
    if mutable:
        ctx.runtime = SearchPathRuntime(state, c)
        ctx.runtime.attach_stats(ctx.stats)
    snapshot = None if ctx.runtime is None else (ctx.runtime.position,
        ctx.runtime.ply_count, ctx.runtime.current_identity, ctx.runtime.runtime_hash,
        tuple(ctx.runtime.history))
    return ctx, snapshot


def assert_restored(ctx, state, snapshot):
    if ctx.runtime is not None:
        ctx.runtime.assert_balanced()
        assert ctx.runtime.position == state.position
        assert ctx.runtime.ply_count == state.ply_count
        assert (ctx.runtime.position, ctx.runtime.ply_count,
                ctx.runtime.current_identity, ctx.runtime.runtime_hash,
                tuple(ctx.runtime.history)) == snapshot


@pytest.mark.parametrize('mutable', [False, True])
@pytest.mark.parametrize('evasion_order', [False, True])
def test_scoped_ordering_keeps_quiet_checking_drop_mate(mutable, evasion_order):
    c = build_4x4_rooks()
    state = make_state(c, ['....', 'R...', '....', 'K.k.'], hands=([('R', 1)], ()))
    ctx, snapshot = context(c, state, _evaluator(c), mutable, evasion_order)
    assert quiescence(state, -INF, INF, 0, 0, ctx) == 999999997
    assert ctx.stats.in_check_qnodes > 0
    assert ctx.stats.checking_drop_qactions > 0
    assert_restored(ctx, state, snapshot)


@pytest.mark.parametrize('mutable', [False, True])
def test_lexical_evasions_do_not_score_the_hard_limit_checked_leaf(mutable):
    c = _king_rook_6(); state = _check_chain_state(c)
    ctx, snapshot = context(c, state, _evaluator(c), mutable, False, hard=4)
    # Start at the configured boundary in a genuine checked nonterminal.
    with pytest.raises(SearchAborted, match='^qsearch_check_hard_limit$'):
        quiescence(state, -INF, INF, 0, 4, ctx)
    assert ctx.stats.qsearch_check_hard_limit_aborts == 1
    assert_restored(ctx, state, snapshot)


@pytest.mark.parametrize('mutable', [False, True])
def test_scoped_ordering_keeps_implicit_semantic_type_change(mutable):
    c = compile_ruleset_for_execution(transform_rules(encoding='effect'))
    state = GameSession(c).state
    cfg = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0,
                           promotion_potential_weight=0)
    ev = Evaluator(c, build_ruleset_profile(c, cfg), cfg)
    scores = []
    for enabled in [False, True]:
        ctx, snapshot = context(c, state, ev, mutable, False)
        ctx.tuning = replace(ctx.tuning, use_ordered_qsearch=enabled)
        ctx.qdepth_limit = 1
        scores.append(quiescence(state, -INF, INF, 0, 0, ctx))
        assert ctx.stats.material_change_qactions > 0
        assert_restored(ctx, state, snapshot)
    assert scores == [1726, 1726]


def test_public_mixed_cancel_keeps_completed_result_and_warm_recovery():
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.cancellation import CancellationToken
    c = build_4x4_rooks(); game = GameSession(c); root = game.state
    tuning = SearchTuning(use_ordered_qsearch=True,
        use_ordered_qsearch_in_check=False, use_root_tactical=False,
        require_full_pv=True)
    player = AlphaBetaPlayer(c, use_disk_cache=False, tuning=tuning)
    limits = SearchLimits(max_depth=2, max_nodes=20000, max_time_seconds=5,
                          quiescence_max_depth=2, quiescence_hard_max_depth=8)
    token = CancellationToken()
    stopped = player.choose_action(game, limits, cancel_token=token,
        progress_callback=lambda depth, nodes, qnodes: token.cancel() if depth == 1 else None)
    assert stopped.termination_reason == 'cancelled'
    assert stopped.completed_depth == 1
    assert stopped.action in game.legal_actions()
    assert game.state == root
    recovered = player.choose_action(game, limits)
    cold = AlphaBetaPlayer(c, use_disk_cache=False, tuning=tuning).choose_action(game, limits)
    assert recovered.completed_depth == cold.completed_depth == 2
    assert (recovered.score, recovered.action, recovered.principal_variation) == (
        cold.score, cold.action, cold.principal_variation)
    assert game.state == root

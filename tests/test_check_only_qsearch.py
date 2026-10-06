"""Opt-in mandatory evasions preserve the default static-leaf contract."""
from dataclasses import replace

import pytest

from generic_chess.ai.alphabeta.search import INF, negamax, _leaf_requires_qsearch, SearchAborted
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from test_qsearch_correctness import _ctx, _evaluator, _king_rook_6, _check_chain_state
from conftest import king_type, make_compiled, make_state


def context(compiled, hard, enabled):
    ctx = _ctx(compiled,_evaluator(compiled),SearchLimits(max_nodes=10000,
               quiescence_max_depth=0,quiescence_hard_max_depth=hard))
    ctx.tuning = replace(ctx.tuning,use_check_only_qsearch=enabled)
    return ctx


def test_default_static_leaf_stays_static_even_in_check():
    compiled = _king_rook_6();state = _check_chain_state(compiled)
    ctx = context(compiled,8,False)
    assert not SearchTuning().use_check_only_qsearch
    assert not _leaf_requires_qsearch(state,ctx)
    assert negamax(state,0,-INF,INF,0,ctx).score == ctx.evaluator.evaluate(state)
    assert ctx.stats.qnodes == 0


def test_check_only_searches_all_evasions_and_reaches_quiet_leaf():
    compiled = _king_rook_6();state = _check_chain_state(compiled)
    ctx = context(compiled,8,True)
    assert _leaf_requires_qsearch(state,ctx)
    score = negamax(state,0,-INF,INF,0,ctx).score
    assert score != ctx.evaluator.evaluate(state)
    assert ctx.stats.in_check_qnodes >= 1
    assert ctx.stats.qdepth_cutoffs > 0


def test_hard_limit_still_aborts_instead_of_scoring_checked_leaf():
    compiled = _king_rook_6();state = _check_chain_state(compiled)
    with pytest.raises(SearchAborted,match='qsearch_check_hard_limit'):
        negamax(state,0,-INF,INF,0,context(compiled,0,True))


def test_check_only_counts_qnodes_in_shared_budget():
    compiled = _king_rook_6()
    state = _check_chain_state(compiled)
    limits = SearchLimits(max_nodes=2, quiescence_max_depth=0,
                          quiescence_hard_max_depth=8)
    ctx = _ctx(compiled, _evaluator(compiled), limits)
    ctx.tuning = replace(ctx.tuning, use_check_only_qsearch=True)
    with pytest.raises(SearchAborted, match='node_limit'):
        negamax(state, 0, -INF, INF, 0, ctx)
    assert ctx.stats.nodes == ctx.stats.qnodes == 1


def test_nonchecking_leaf_never_enters_qsearch():
    compiled = make_compiled(6,[king_type()])
    state = make_state(compiled,['.....K','......','......','......','......','k.....'])
    a=context(compiled,8,False);b=context(compiled,8,True)
    assert not _leaf_requires_qsearch(state,b)
    assert negamax(state,0,-INF,INF,0,a).score == negamax(state,0,-INF,INF,0,b).score
    assert a.stats.qnodes == b.stats.qnodes == 0


def test_terminal_leaf_has_priority_over_check_only(monkeypatch):
    from scripts.chess_development import root_from_fen
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.western_chess import build_western_chess_ruleset
    import generic_chess.ai.alphabeta.search as search
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    state = root_from_fen('7k/6Q1/5K2/8/8/8/8/8 b - - 0 1', compiled)
    assert state.terminal_status.is_terminal
    def forbidden(*args):
        raise AssertionError('terminal must not enter checking-leaf logic')
    monkeypatch.setattr(search, '_leaf_requires_qsearch', forbidden)
    ctx = context(compiled, 8, True)
    assert negamax(state, 0, -INF, INF, 0, ctx).score < -1000000
    assert ctx.stats.qnodes == 0


def test_native_and_authoritative_root_check_only_agree():
    from scripts.chess_development import compare_case
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.western_chess import build_western_chess_ruleset
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    if provider is None:
        pytest.skip('optional native extension unavailable')
    case = dict(id='checking-rook', fen='3k4/2p5/8/8/8/8/8/3R3K w - - 0 1',
                accepted_uci=['d1d7'], answer_basis='legality control, not oracle answer')
    limits = SearchLimits(max_depth=1, max_nodes=8192, max_time_seconds=5,
                          quiescence_max_depth=0, quiescence_hard_max_depth=8)
    tuning = SearchTuning(use_root_tactical=False, use_check_only_qsearch=True)
    a = compare_case(case, compiled, limits, ordering=True, use_tt=True, tuning=tuning)
    b = compare_case(case, compiled, limits, provider=provider, ordering=True, use_tt=True, tuning=tuning)
    assert all(r['completed'] for r in a['rows'] + b['rows'])
    assert all(r['statistics']['in_check_qnodes'] > 0 for r in a['rows'] + b['rows'])
    assert [(r['move'], r['score']) for r in a['rows']] == [(r['move'], r['score']) for r in b['rows']]

"""Actual exposed full-history Core contracts for one-path check extension."""
from pathlib import Path
from dataclasses import replace
import json
import pytest
from scripts.verify_leaper_pvs_quality_pilot import load,action
from scripts.leaper_pvs_quality_pilot import make_session
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime

BASE=Path('docs/research/data/leaper_check_extension_20261028/core-witness')
@pytest.fixture(scope='module')
def roots():
    if not BASE.exists():pytest.skip('current fixed development witness artifact not installed')
    rows={r['id']:r for r in load(Path('docs/research/data/leaper_new_family_pvs_20261028/inputs.json'))['rows']}
    result=[]
    for w in load(BASE/'witnesses.json')[::2]:
        c,_=make_session(rows[w['case_id']]);s=GameSession.replay(c,deserialize_game_record(json.dumps(w['record'])))
        result.append((c,s,w))
    assert len(result)==6
    return result

def context(root,tt=None,full=False,pvs=False,cancel=None):
    c,s,w=root;p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True)
    provider=p._native_legality_provider
    rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=provider,availability_provider=provider.has_legal_action,check_provider=provider.in_check)
    ctx=S._Context(c,p._evaluator,tt if tt is not None else TranspositionTable(),SearchStatistics(),S._Budget(SearchLimits(max_nodes=200000,max_time_seconds=5,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel),SearchTuning(use_one_check_extension=True,require_full_pv=full,use_pvs=pvs),True,True,4,8,None,runtime=rt)
    return ctx

@pytest.mark.parametrize('index',range(6))
def test_actual_history_cross_bank_cold_hot_off_and_pv(roots,index):
    root=roots[index];c,s,w=root;cold={}
    for e in (0,1):
        ctx=context(root);r=S.negamax(ctx.runtime.state,1,-S.INF,S.INF,0,ctx,remaining_extensions=e);cold[e]=r
        ctx.runtime.assert_balanced();assert r.best_action in s.legal_actions()
        pv=GameSession.replay(c,s.to_record())
        for a in r.pv:pv.submit(a)
        assert ctx.stats.main_extension_max_path<=1
        for warm_e in (0,1):
            tt=TranspositionTable();warm=context(root,tt);S.negamax(warm.runtime.state,1,-S.INF,S.INF,0,warm,remaining_extensions=warm_e)
            hot=context(root,tt,full=True);got=S.negamax(hot.runtime.state,1,-S.INF,S.INF,0,hot,remaining_extensions=e)
            assert got.score==r.score;hot.runtime.assert_balanced()
            pv=GameSession.replay(c,s.to_record())
            for a in got.pv:pv.submit(a)
        no=context(root);no.use_tt=False
        assert S.negamax(no.runtime.state,1,-S.INF,S.INF,0,no,remaining_extensions=e).score==r.score


def test_actual_qleaf_no_extension_and_cancellation_restores_complete_history(roots):
    root=roots[0];c,s,w=root
    for e in (0,1):
        ctx=context(root);S.negamax(ctx.runtime.state,0,-S.INF,S.INF,0,ctx,remaining_extensions=e)
        assert ctx.stats.main_check_extensions==0;ctx.runtime.assert_balanced()
    class CancelInside:
        ctx=None
        def is_cancelled(self):return self.ctx is not None and self.ctx.runtime.depth>0 and self.ctx.stats.main_extension_max_path>0
    token=CancelInside();ctx=context(root,cancel=token);token.ctx=ctx
    before=ctx.runtime.state
    with pytest.raises(S.SearchAborted,match='cancelled'):S.negamax(ctx.runtime.state,1,-S.INF,S.INF,0,ctx)
    ctx.runtime.assert_balanced();assert ctx.runtime.state==before and s.to_record()==root[1].to_record()


def test_actual_checked_q_hard_cap_still_aborts_not_exact_value(roots):
    ctx=context(roots[0]);ctx.qhard_depth_limit=0
    with pytest.raises(S.SearchAborted,match='qsearch_check_hard_limit'):
        S.negamax(ctx.runtime.state,0,-S.INF,S.INF,0,ctx)
    ctx.runtime.assert_balanced();assert ctx.stats.main_check_extensions==0 and len(ctx.tt)==0


@pytest.mark.parametrize('reason',['max_ply','repetition'])
def test_real_terminal_history_precedes_any_extension_or_tt_value(reason):
    games=load(Path('docs/research/data/leaper_new_family_pvs_20261028/results/games.json'))
    rootrows={r['id']:r for r in load(Path('docs/research/data/leaper_new_family_pvs_20261028/inputs.json'))['rows']}
    g=next(g for g in games if g['Core_terminal']['status']==reason)
    c,_=make_session(rootrows[g['case_id']]);s=GameSession.replay(c,deserialize_game_record(json.dumps(g['final_record'])))
    assert s.state.terminal_status.is_terminal
    before=s.to_record();ctx=context((c,s,{}));result=S.negamax(ctx.runtime.state,3,-S.INF,S.INF,0,ctx)
    assert result.score==0 and result.best_action is None
    assert ctx.stats.main_check_extensions==ctx.stats.tt_probes==ctx.stats.tt_stores==0
    ctx.runtime.assert_balanced();assert s.to_record()==before


def test_public_optin_rejects_noncertified_rider_scope_without_affecting_default():
    from ai_fixtures import build_4x4_rooks
    c=build_4x4_rooks()
    with pytest.raises(ValueError,match='certified pure-Leaper executable IR'):
        AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_one_check_extension=True))
    assert AlphaBetaPlayer(c,use_disk_cache=False)._tuning.use_one_check_extension is False

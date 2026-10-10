"""Experimental shared-budget reserve contracts, not product adoption tests."""
import pytest
from scripts.reserve_refresh_diagnostic import make_refresh, ORIGINAL
from scripts.search_backend_comparison import CoreBoard
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession


def fixture():
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    b=CoreBoard(dict(game='chess',setup='k4b2/6p1/8/8/8/6Q1/8/6K1 w - - 0 1',moves=''),c)
    s=GameSession(c);s._state=b.initial;s._search_history_witnesses=b.witnesses
    return s,b.material,b


def choose(monkeypatch,s,e,events,*,naive=False,token=None,phase=None,limits=None):
    monkeypatch.setattr(pm,'run_root_search',make_refresh(events,naive,token,phase,s.state))
    return AlphaBetaPlayer(s.compiled,evaluator_override=e,use_native_semantic_legality=False).choose_action(
        s,limits or SearchLimits(max_depth=1,max_time_seconds=5,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=token)


def test_same_depth_tt_is_not_evidence_of_q1_work(monkeypatch):
    s,e,b=fixture();naive=[];safe=[]
    a=choose(monkeypatch,s,e,naive,naive=True)
    d=choose(monkeypatch,s,e,safe)
    assert naive[-1]['qnodes']==naive[0]['qnodes']
    assert naive[-1]['nodes']==naive[0]['nodes']+1
    assert safe[-1]['qnodes']>safe[0]['qnodes']
    # Independent specialized rules verify the q0 move actually drops a queen.
    assert b.label(a.action)=='g3g7'
    import chess
    native=chess.Board('k4b2/6p1/8/8/8/6Q1/8/6K1 w - - 0 1')
    native.push_uci('g3g7');assert chess.Move.from_uci('f8g7') in native.legal_moves
    assert native.piece_at(chess.G7).piece_type==chess.QUEEN
    assert b.label(d.action)!='g3g7'
    assert s.state==b.initial and b.restored()


@pytest.mark.parametrize('phase',['begin','complete'])
def test_cancel_keeps_completed_result_and_internal_root(monkeypatch,phase):
    s,e,b=fixture();events=[];token=CancellationToken()
    d=choose(monkeypatch,s,e,events,token=token,phase=phase,limits=SearchLimits(max_depth=2,max_time_seconds=5))
    assert d.completed_depth==1 and d.termination_reason=='cancelled'
    kept=next(x for x in events if x['phase']==('reserve' if phase=='begin' else 'complete'))
    from scripts.research_record import record_value
    assert record_value(d.action)==kept['action'] and d.score==kept['score']
    assert all(x['runtime_restored'] and x['runtime_balanced'] and x['runtime_depth']==0 for x in events)
    assert len({x['deadline'] for x in events})==1
    assert s.state==b.initial


def test_node_budget_is_shared_with_refresh(monkeypatch):
    s,e,b=fixture()
    monkeypatch.setattr(pm,'run_root_search',ORIGINAL)
    base=AlphaBetaPlayer(s.compiled,evaluator_override=e,use_native_semantic_legality=False).choose_action(s,SearchLimits(max_depth=1,max_time_seconds=5))
    events=[]
    d=choose(monkeypatch,s,e,events,limits=SearchLimits(max_depth=2,max_nodes=base.nodes+base.qnodes+2,max_time_seconds=5))
    assert d.completed_depth==1 and d.termination_reason=='node_limit'
    assert d.action==base.action and d.score==base.score
    assert events[-1]['phase']=='aborted' and events[-1]['runtime_restored']
    assert d.nodes+d.qnodes>=base.nodes+base.qnodes+2
    assert len({x['budget_identity'] for x in events})==1


def test_explicit_qzero_has_no_refresh_or_extra_work(monkeypatch):
    s,e,b=fixture();limits=SearchLimits(max_depth=2,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=0)
    monkeypatch.setattr(pm,'run_root_search',ORIGINAL)
    a=AlphaBetaPlayer(s.compiled,evaluator_override=e,use_native_semantic_legality=False).choose_action(s,limits)
    events=[];d=choose(monkeypatch,s,e,events,limits=limits)
    assert not events
    assert (d.action,d.score,d.nodes,d.qnodes,d.completed_depth)==(a.action,a.score,a.nodes,a.qnodes,a.completed_depth)


@pytest.mark.parametrize('nodes',[4,32])
def test_abort_before_first_completion_preserves_original_fallback(monkeypatch,nodes):
    s,e,b=fixture();limits=SearchLimits(max_depth=2,max_nodes=nodes,max_time_seconds=5)
    monkeypatch.setattr(pm,'run_root_search',ORIGINAL)
    a=AlphaBetaPlayer(s.compiled,evaluator_override=e,use_native_semantic_legality=False).choose_action(s,limits)
    events=[];d=choose(monkeypatch,s,e,events,limits=limits)
    assert a.completed_depth==d.completed_depth==0
    assert not events
    assert (d.action,d.score,d.nodes,d.qnodes,d.termination_reason)==(a.action,a.score,a.nodes,a.qnodes,a.termination_reason)
    assert s.state==b.initial


def test_cancel_from_progress_keeps_original_completed_reserve(monkeypatch):
    s,e,b=fixture();events=[];token=CancellationToken()
    monkeypatch.setattr(pm,'run_root_search',make_refresh(events,token=token,expected_state=s.state))
    def progress(*_):token.cancel()
    d=AlphaBetaPlayer(s.compiled,evaluator_override=e,use_native_semantic_legality=False).choose_action(
        s,SearchLimits(max_depth=2,max_time_seconds=5),cancel_token=token,progress_callback=progress)
    assert d.completed_depth==1 and d.termination_reason=='cancelled'
    from scripts.research_record import record_value
    assert record_value(d.action)==events[0]['action'] and d.score==events[0]['score']
    assert events[-1]['phase']=='aborted' and all(x['runtime_restored'] for x in events)


@pytest.mark.parametrize('use_tt',[False,True])
def test_phase_bypass_never_uses_tt_in_cheap_or_refresh(monkeypatch,use_tt):
    from generic_chess.ai.alphabeta import search
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    s,e,b=fixture();active=[];calls=[];old=search.negamax
    def traced(state,depth,alpha,beta,ply,ctx,*args,**kwargs):
        active.append(ctx)
        try:return old(state,depth,alpha,beta,ply,ctx,*args,**kwargs)
        finally:active.pop()
    monkeypatch.setattr(search,'negamax',traced)
    class TracedTT(TranspositionTable):
        def probe(self,key):
            assert active
            ctx=active[-1];calls.append(('probe',search._ordinary_qdepth_limit(ctx)))
            assert use_tt and ctx.first_main_iteration_complete and ctx.qdepth_limit==4
            return super().probe(key)
        def store(self,*args):
            assert active
            ctx=active[-1];calls.append(('store',search._ordinary_qdepth_limit(ctx)))
            assert use_tt and ctx.first_main_iteration_complete and ctx.qdepth_limit==4
            return super().store(*args)
    events=[];monkeypatch.setattr(pm,'run_root_search',make_refresh(events,expected_state=s.state,tt_policy='phase_bypass'))
    p=AlphaBetaPlayer(s.compiled,evaluator_override=e,use_native_semantic_legality=False,use_tt=use_tt);p._tt=TracedTT()
    d=p.choose_action(s,SearchLimits(max_depth=2,max_nodes=10000,max_time_seconds=5))
    assert not active and s.state==b.initial
    assert all(x['runtime_restored'] and x['runtime_balanced'] for x in events)
    assert d.completed_depth>=1 and events[-1]['phase']=='complete'
    assert bool(calls)==use_tt
    assert all(q==4 for _,q in calls)

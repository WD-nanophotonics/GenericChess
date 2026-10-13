"""Readonly child-check transport preserves Core commits and default behavior."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.native import native_available
from scripts.search_backend_comparison import CASES,CoreBoard,Material
def root(name):
    case=next(x for x in CASES if x['id']==name)
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess' if case['game']=='chess' else 'standard_shogi'))
    return c,CoreBoard(case,c)
def sess(b):return SimpleNamespace(state=b.initial,_search_witnesses=b.witnesses)
def saved(r):return r.position,tuple(r.history),r.ply_count,r.runtime_hash,r.terminal_status,r.depth
@pytest.mark.skipif(not native_available(),reason='native unavailable')
@pytest.mark.parametrize('name',['chess-ep','shogi-promotion','shogi-drop'])
def test_actual_public_check_handoff_preserves_full_decision_history_and_counts(name):
    c,b=root(name);out=[];session=sess(b);before_state=session.state;before_witnesses=session._search_witnesses
    for enabled in [False,True]:
        p=AlphaBetaPlayer(c,evaluator_override=Material(b.game),use_disk_cache=False,use_native_semantic_availability=True,use_native_semantic_check=enabled,tuning=SearchTuning(use_root_tactical=False,require_full_pv=True))
        d=p.choose_action(session,SearchLimits(max_depth=1,max_nodes=100000,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=8))
        assert d.completed_depth==1 and d.native_legality_fallbacks==0
        out.append((d.action,d.score,d.principal_variation,d.nodes,d.qnodes))
        check=p.native_legality_provider.check_metrics;avail=p.native_legality_provider.availability_metrics
        if enabled:
            assert check['queries']>0 and check['imports']==check['queries']
            assert avail['reused_imports']>0 and avail['imports']+avail['reused_imports']==avail['queries']
        else:
            assert check=={} and p._check_provider is None
            assert 'reused_imports' not in avail
        assert session.state is before_state and session._search_witnesses==before_witnesses
    assert out[0]==out[1]
@pytest.mark.skipif(not native_available(),reason='native unavailable')
def test_handoff_is_one_use_exact_object_and_never_caches_a_boolean(monkeypatch):
    from generic_chess.native import semantic
    c,b=root('chess-ep');p=NativeSemanticLegalityProvider.try_create(c,strict=True);pos=b.initial.position
    original=semantic.has_legal_action;calls=[]
    def query(*args):
        calls.append(1);return original(*args)
    monkeypatch.setattr(semantic,'has_legal_action',query)
    assert p.in_check(pos,pos.side_to_move)==semantic_engine_for(c).in_check(pos,pos.side_to_move)
    p.has_legal_action(pos);p.has_legal_action(pos)
    assert len(calls)==2 and p.availability_metrics['reused_imports']==1 and p.availability_metrics['imports']==1
    equal_copy=replace(pos)
    assert equal_copy==pos and equal_copy is not pos
    p.in_check(pos,pos.side_to_move);p.has_legal_action(equal_copy)
    assert len(calls)==3 and p.availability_metrics['reused_imports']==1 and p.availability_metrics['imports']==2
@pytest.mark.skipif(not native_available(),reason='native unavailable')
def test_check_queries_explicit_owner_and_rejects_foreign_source(monkeypatch):
    from generic_chess.native import semantic
    c,b=root('chess-ep');other,foreign=root('shogi-drop');p=NativeSemanticLegalityProvider.try_create(c,strict=True);owners=[]
    def query(rules,position,side):owners.append(side);return side==1
    monkeypatch.setattr(semantic,'in_check',query)
    assert p.in_check(b.initial.position,0) is False and p.in_check(b.initial.position,1) is True
    assert owners==[0,1]
    with pytest.raises(ValueError,match='source mismatch'):p.in_check(foreign.initial.position,0)
    with pytest.raises(ValueError,match='side'):p.in_check(b.initial.position,True)
def test_check_decline_and_required_failure_restore_exact_runtime():
    c,b=root('chess-ep');calls=[]
    def decline(position,side,checkpoint=None):calls.append((position,side));return None
    normal=SearchPathRuntime.from_state(b.initial,c,history_witnesses=b.witnesses)
    candidate=SearchPathRuntime.from_state(b.initial,c,history_witnesses=b.witnesses,check_provider=decline)
    action=normal.legal_actions()[0];before=saved(candidate)
    normal.push(action);candidate.push(action)
    assert calls and saved(candidate)==saved(normal)
    candidate.pop();normal.pop();assert saved(candidate)==before
    def error(*args,**kwargs):raise RuntimeError('required child check')
    candidate._check_provider=error
    with pytest.raises(RuntimeError,match='required child check'):candidate.push(action)
    assert saved(candidate)==before
    candidate._check_provider=decline;candidate.push(action);candidate.pop();assert saved(candidate)==before
@pytest.mark.skipif(not native_available(),reason='native unavailable')
def test_native_check_required_failure_and_postquery_poll_leave_no_handoff_or_runtime_change(monkeypatch):
    from generic_chess.native import semantic
    c,b=root('chess-ep');p=NativeSemanticLegalityProvider.try_create(c,strict=True)
    r=SearchPathRuntime.from_state(b.initial,c,history_witnesses=b.witnesses,legal_binding_provider=p,availability_provider=p.has_legal_action,check_provider=p.in_check)
    action=r.legal_actions()[0];before=saved(r);real=semantic.in_check
    def fail(*args):raise RuntimeError('native check failure')
    monkeypatch.setattr(semantic,'in_check',fail)
    with pytest.raises(RuntimeError,match='native check failure'):r.push(action)
    assert saved(r)==before and p._metrics_local.check_handoff is None
    monkeypatch.setattr(semantic,'in_check',real)
    n=0
    def poll():
        nonlocal n
        n+=1
        if n==2:raise RuntimeError('postquery poll')
    with pytest.raises(RuntimeError,match='postquery poll'):p.in_check(r.position,r.position.side_to_move,checkpoint=poll)
    assert p._metrics_local.check_handoff is None and saved(r)==before
    r.push(action);r.pop();assert saved(r)==before
def test_missing_native_provider_retains_core_and_explicit_decline_override(monkeypatch):
    c,b=root('chess-ep')
    monkeypatch.setattr(NativeSemanticLegalityProvider,'try_create',lambda compiled:None)
    called=[]
    def decline(position,side,checkpoint=None):called.append(side);return None
    p=AlphaBetaPlayer(c,evaluator_override=Material('chess'),use_disk_cache=False,use_native_semantic_check=True,check_provider=decline)
    d=p.choose_action(sess(b),SearchLimits(max_depth=1,max_nodes=100000,max_time_seconds=5,quiescence_max_depth=0))
    assert p.use_native_semantic_check and p.native_legality_provider is None and called and d.completed_depth==1
    fallback=AlphaBetaPlayer(c,evaluator_override=Material('chess'),use_disk_cache=False,use_native_semantic_check=True)
    assert fallback._check_provider is None
@pytest.mark.skipif(not native_available(),reason='native unavailable')
@pytest.mark.parametrize('max_ply',[1,2])
def test_short_s4_reply_decline_preserves_core_terminal_precedence(max_ply):
    c=compile_ruleset_for_execution(replace(build_builtin_ruleset('standard_shogi'),max_ply=max_ply))
    b=CoreBoard(next(x for x in CASES if x['id']=='shogi-drop'),c);p=NativeSemanticLegalityProvider.try_create(c,strict=True)
    pos=b.initial.position
    assert p.in_check(pos,pos.side_to_move)==semantic_engine_for(c).in_check(pos,pos.side_to_move)
    value=p.has_legal_action(pos)
    assert value is None if max_ply==1 else value==semantic_engine_for(c).has_legal_action(pos)
    assert p.availability_metrics['declines']==int(max_ply==1)

def test_pass_keeps_core_nonchecking_responsibility_and_consecutive_draw():
    from test_runtime_action_history_key import pair
    from generic_chess.core.actions import PassAction
    c,session,_=pair()
    def must_not_call(*args,**kwargs):raise AssertionError('pass must not query child check')
    r=SearchPathRuntime.from_state(session.state,c,history_witnesses=session._search_witnesses,check_provider=must_not_call)
    before=saved(r)
    r.push(PassAction())
    assert r.history[-1].gave_check is False and r.terminal_status.is_terminal
    assert r.terminal_status.winner is None
    r.pop();assert saved(r)==before

def test_nonboolean_check_response_is_required_error_with_balanced_undo():
    c,b=root('chess-ep')
    r=SearchPathRuntime.from_state(b.initial,c,history_witnesses=b.witnesses,check_provider=lambda *args,**kwargs:1)
    action=r.legal_actions()[0];before=saved(r)
    with pytest.raises(TypeError,match='bool or None'):r.push(action)
    assert saved(r)==before

@pytest.mark.skipif(not native_available(),reason='native unavailable')
def test_availability_entry_cancel_consumes_handoff_and_same_object_retry_imports_fresh():
    c,b=root('chess-ep');p=NativeSemanticLegalityProvider.try_create(c,strict=True);held=[]
    fault=RuntimeError('availability entry cancellation')
    def check(position,side,checkpoint=None):
        value=p.in_check(position,side,checkpoint=checkpoint);held.append(position);return value
    def availability(position,checkpoint=None):
        assert position is held[-1]
        def interrupted():raise fault
        return p.has_legal_action(position,checkpoint=interrupted)
    r=SearchPathRuntime.from_state(b.initial,c,history_witnesses=b.witnesses,legal_binding_provider=p,availability_provider=availability,check_provider=check)
    action=r.legal_actions()[0];before=saved(r);counts=r._snapshot;context=r._history_context
    with pytest.raises(RuntimeError) as caught:r.push(action)
    assert caught.value is fault and saved(r)==before
    assert r._snapshot==counts and r._history_context==context
    assert p.availability_metrics['queries']==0
    assert p._metrics_local.check_handoff is None
    position=held[-1];imports=p.availability_metrics['imports']
    assert p.has_legal_action(position)==semantic_engine_for(c).has_legal_action(position)
    assert p.availability_metrics['imports']==imports+1

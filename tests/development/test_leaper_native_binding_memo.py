"""Native binding memo equivalence, never a cached-legal-set claim."""
from dataclasses import replace,fields
from collections import Counter
import pytest
from test_leaper_threat_ordering import fixture
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.semantic_executor import _ActionBinding
from generic_chess.core.pieces import Piece
from generic_chess.core.errors import IllegalActionError
from scripts.leaper_native_binding_memo import NativeBindingMemo

def context():
    c,s=fixture();p=NativeSemanticLegalityProvider.try_create(c);assert p is not None;m=NativeBindingMemo(p);assert m.admitted;return c,s,p,m

def test_actual_Native_pairs_equal_original_builder_on_cold_and_hot_hits():
    c,s,p,m=context();original=p.engine._make_binding_from_action
    with m.installed():
        first=p(s.state.position,0);second=p(s.state.position,0)
        assert first==second and m.metrics['hits']>=len(first)
        for public,(action,binding) in second:assert binding==original(s.state.position,action,p.pattern_by_id[action.pattern_id])
    assert not m._installed and not m.cache and p.engine._make_binding_from_action==original
    assert {f.name for f in fields(_ActionBinding)}=={'pattern','geometry_id','actor_owner','actor_type','actor_base','actor_current','source','target','promotion_target_id','path'}

def test_actor_base_change_is_distinct_even_when_action_current_type_matches():
    c,s,p,m=context();pos=s.state.position
    with m.installed():
        pairs=p(pos,0);public,(action,binding)=next(x for x in pairs if x[1][0].actor_type=='W');piece=pos.board[action.source];board=list(pos.board);board[action.source]=replace(piece,base_type_id='N',promoted=True);changed=replace(pos,board=tuple(board));before=m.metrics['misses'];value=m.bind(changed,action,p.pattern_by_id[action.pattern_id]);reference=m.original(changed,action,p.pattern_by_id[action.pattern_id])
        assert value==reference and value.actor_base=='N' and value!=binding and m.metrics['misses']==before+1
        assert m.bind(pos,action,p.pattern_by_id[action.pattern_id])==binding

def test_cached_binding_does_not_cache_or_authorize_current_legal_actions():
    c,s,p,m=context();pos=s.state.position
    with m.installed():
        old=p(pos,0);public,(action,binding)=next(x for x in old if x[1][0].actor_type=='W' and pos.board[x[1][0].target] is None);board=list(pos.board);board[action.target]=Piece(pos.side_to_move,'N','N');blocked=replace(pos,board=tuple(board));new=p(blocked,0)
        assert public not in [x[0] for x in new]
        # Construction alone remains possible, exactly as original builder;
        # Native/Core S1/S3 legality is an independent current-state decision.
        assert m.bind(blocked,action,p.pattern_by_id[action.pattern_id])==m.original(blocked,action,p.pattern_by_id[action.pattern_id])==binding

def test_failed_builder_does_not_insert_and_bounded_eviction_preserves_values():
    c,s,p,m=context();m.maximum=2;pos=s.state.position
    with m.installed():
        pairs=p(pos,0);assert m.metrics['clears']>0 and len(m.cache)<=2
        action=pairs[0][1][0];board=list(pos.board);board[action.source]=None;invalid=replace(pos,board=tuple(board));before=len(m.cache)
        with pytest.raises(IllegalActionError):m.bind(invalid,action,p.pattern_by_id[action.pattern_id])
        assert len(m.cache)==before

def test_cancelled_frontier_keeps_original_exception_and_restores_engine():
    c,s,p,m=context();old=p.engine._make_binding_from_action;count=0
    def stop():
        nonlocal count
        count+=1
        if count==3:raise RuntimeError('original Native checkpoint')
    with pytest.raises(RuntimeError,match='original Native checkpoint'):
        with m.installed():p(s.state.position,0,checkpoint=stop)
    assert p.engine._make_binding_from_action==old and not m._installed and not m.cache

def test_capture_only_IR_is_unsupported_and_uses_original_builder():
    c,s,p,m=context();changed=replace(c,ir=replace(c.ir,patterns=tuple(x for x in c.ir.patterns if x.target.kind!='target_empty')));n=NativeSemanticLegalityProvider.try_create(changed);m=NativeBindingMemo(n);assert not m.admitted
    with m.installed():pairs=n(s.state.position,0)
    assert m.metrics['hits']==0
    for public,(action,binding) in pairs:assert binding==m.original(s.state.position,action,n.pattern_by_id[action.pattern_id])


def test_actual_Player_fixedwork_full_nonclock_parity(tmp_path):
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    from scripts.leaper_boolean_cost_pilot import signature
    from scripts.research_record import record_value,write_record
    c,s=fixture();before=s.to_record();decisions=[]
    for on in (False,True):
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
        if on:
            m=NativeBindingMemo(p.native_legality_provider)
            with m.installed():d=p.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=4,quiescence_hard_max_depth=8))
            assert m.metrics['hits']>0 and not m._installed
        else:d=p.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=4,quiescence_hard_max_depth=8))
        write_record(tmp_path/('binding-'+str(on)+'.json'),{'decision':d,'metrics':m.metrics if on else None});decisions.append(d);assert s.to_record()==before and d.runtime_depth_balanced
    assert signature(record_value(decisions[0]))==signature(record_value(decisions[1]))

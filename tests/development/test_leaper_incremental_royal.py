"""Incremental provider semantic/cancel/fallback controls, not timing samples."""
from dataclasses import replace
import pytest
from test_leaper_threat_ordering import fixture
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.leaper_incremental_royal import IncrementalRoyalProvider
from scripts.verify_leaper_incremental_royal import signature
from scripts.leaper_boolean_cost_pilot import signature as decision_signature
from scripts.research_record import record_value,write_record

def context():
    c,s=fixture();native=NativeSemanticLegalityProvider.try_create(c);assert native is not None;m=IncrementalRoyalProvider(c,native);rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=native,availability_provider=m.has_legal_action,check_provider=m.in_check);return c,s,m,rt

def test_predicted_guard_matches_complete_Core_state_and_roundtrip():
    c,s,m,rt=context();actions=rt.legal_actions();before=signature(rt)
    with m.installed():
        for action in actions:
            with rt.pushed(action):
                assert m.cache.position is rt.position
                for side in (0,1):assert m.in_check(rt.position,side)==m.engine.in_check(rt.position,side)
                assert m.has_legal_action(rt.position)==m.engine.has_legal_action(rt.position)
            assert signature(rt)==before
        assert not m.undo
    assert m.metrics['guard_misses']==0 and m.metrics['availability_certificates']>0

def test_actual_guard_mismatch_never_uses_wrong_bitboards(monkeypatch):
    c,s,m,rt=context();old=m._predict
    def wrong(parent,action):
        value=old(parent,action)
        if value:value.position=replace(value.position,side_to_move=1-value.position.side_to_move);value.boards={(o,t):0 for o,t in value.boards}
        return value
    monkeypatch.setattr(m,'_predict',wrong);before=signature(rt)
    with m.installed():
        for action in rt.legal_actions()[:3]:
            with rt.pushed(action):
                assert m.in_check(rt.position,rt.position.side_to_move)==m.engine.in_check(rt.position,rt.position.side_to_move)
                assert m.has_legal_action(rt.position)==m.engine.has_legal_action(rt.position)
            assert signature(rt)==before
    assert m.metrics['check_fast']==0 and m.metrics['availability_certificates']==0 and m.metrics['guard_misses']>0

@pytest.mark.parametrize('stage',['check','availability'])
def test_cancel_after_fast_predicate_restores_full_Runtime_and_private_stack(stage):
    c,s,m,rt=context();action=rt.legal_actions()[0];before=signature(rt)
    def stop():
        key='check_fast' if stage=='check' else 'availability_certificates'
        if m.metrics[key]>0:raise RuntimeError('cancel after '+stage)
    with m.installed():
        with pytest.raises(RuntimeError,match='cancel after'):rt.push(action,checkpoint=stop)
        assert not m.undo and signature(rt)==before and m.metrics['rollbacks']==1
    rt.assert_balanced()

def test_capture_only_IR_is_not_admitted_and_falls_back_to_actual_Core():
    c,s,m,rt=context();changed=replace(c,ir=replace(c.ir,patterns=tuple(p for p in c.ir.patterns if p.target.kind!='target_empty')));native=NativeSemanticLegalityProvider.try_create(changed);n=IncrementalRoyalProvider(changed,native);assert not n.admitted
    for side in (0,1):assert n.in_check(s.state.position,side)==n.engine.in_check(s.state.position,side)
    assert n.has_legal_action(s.state.position)==n.engine.has_legal_action(s.state.position)
    assert n.metrics['check_fast']==n.metrics['availability_certificates']==0

def test_real_Player_fixed_work_parity_and_hook_cleanup(tmp_path):
    c,s=fixture();before=s.to_record();decisions=[];push=SearchPathRuntime.push;pop=SearchPathRuntime.pop
    for on in (False,True):
        player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=False,use_aspiration=False),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
        if on:
            model=IncrementalRoyalProvider(c,player.native_legality_provider);player._check_provider=model.in_check;player._availability_provider=model.has_legal_action
            with model.installed():d=player.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=4,quiescence_hard_max_depth=8))
        else:d=player.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=4,quiescence_hard_max_depth=8))
        write_record(tmp_path/('on-'+str(on)+'.json'),{'decision':d,'metrics':model.metrics if on else None});decisions.append(d);assert d.runtime_depth_balanced and s.to_record()==before and SearchPathRuntime.push is push and SearchPathRuntime.pop is pop
    assert decision_signature(record_value(decisions[0]))==decision_signature(record_value(decisions[1]))

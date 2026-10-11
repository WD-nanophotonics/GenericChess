"""Actual public opt-in keeps Core terminal/history ownership and default policy."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.native import native_available
from scripts.search_backend_comparison import CASES,CoreBoard,Material

def root(case_id):
    case=next(x for x in CASES if x['id']==case_id)
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess' if case['game']=='chess' else 'standard_shogi'))
    return c,CoreBoard(case,c)

def session(core):return SimpleNamespace(state=core.initial,_search_witnesses=core.witnesses)

@pytest.mark.skipif(not native_available(),reason='native unavailable')
@pytest.mark.parametrize('case_id',['chess-ep','chess-promotion','shogi-promotion','shogi-drop'])
def test_public_flag_matches_core_complete_decision_and_preserves_root(case_id):
    c,core=root(case_id);decisions=[]
    for enabled in [False,True]:
        player=AlphaBetaPlayer(c,evaluator_override=Material(core.game),use_disk_cache=False,use_native_semantic_availability=enabled)
        saved=core.initial
        d=player.choose_action(session(core),SearchLimits(max_depth=1,max_nodes=100000,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=8))
        assert d.completed_depth==1 and core.initial==saved
        decisions.append((d.action,d.score,d.principal_variation,d.result_ordinary_qdepth))
        metrics=player.native_legality_provider.availability_metrics
        if enabled:assert metrics['queries']>0 and metrics['imports']==metrics['queries'] and metrics['declines']==0
        else:assert metrics=={} and player._availability_provider is None
    assert decisions[0]==decisions[1]

@pytest.mark.skipif(not native_available(),reason='native unavailable')
@pytest.mark.parametrize('max_ply',[1,2])
def test_s4_short_cutoff_declines_to_core_without_using_empty_legal_frontier(max_ply):
    c=compile_ruleset_for_execution(replace(build_builtin_ruleset('standard_shogi'),max_ply=max_ply))
    core=CoreBoard(next(x for x in CASES if x['id']=='shogi-drop'),c)
    provider=NativeSemanticLegalityProvider.try_create(c,strict=True)
    value=provider.has_legal_action(core.runtime.position)
    assert value is None if max_ply==1 else value==semantic_engine_for(c).has_legal_action(core.runtime.position)
    assert provider.availability_metrics['declines']==int(max_ply==1)
    assert provider.availability_metrics['queries']==int(max_ply!=1)

@pytest.mark.skipif(not native_available(),reason='native unavailable')
def test_availability_can_be_opted_in_with_core_legality_and_explicit_override_wins():
    c,core=root('chess-ep');called=[]
    def override(position,checkpoint=None):
        called.append(position)
        if checkpoint:checkpoint()
        return None
    player=AlphaBetaPlayer(c,evaluator_override=Material('chess'),use_native_semantic_legality=False,use_native_semantic_availability=True,availability_provider=override)
    d=player.choose_action(session(core),SearchLimits(max_depth=1,max_nodes=100000,max_time_seconds=5,quiescence_max_depth=0))
    assert called and d.completed_depth==1 and d.native_legality_calls==0
    assert player.native_legality_provider.availability_metrics=={}
    automatic=AlphaBetaPlayer(c,evaluator_override=Material('chess'),use_native_semantic_legality=False,use_native_semantic_availability=True)
    d2=automatic.choose_action(session(core),SearchLimits(max_depth=1,max_nodes=100000,max_time_seconds=5,quiescence_max_depth=0))
    assert d2.native_legality_calls==0 and automatic.native_legality_provider.availability_metrics['queries']>0
    assert (d.action,d.score)==(d2.action,d2.score)

def test_unsupported_provider_keeps_core_fallback_and_default_off(monkeypatch):
    c,core=root('chess-ep')
    monkeypatch.setattr(NativeSemanticLegalityProvider,'try_create',lambda compiled:None)
    player=AlphaBetaPlayer(c,evaluator_override=Material('chess'),use_native_semantic_availability=True)
    assert player.use_native_semantic_availability and player._availability_provider is None
    d=player.choose_action(session(core),SearchLimits(max_depth=1,max_nodes=100000,max_time_seconds=5,quiescence_max_depth=0))
    assert d.completed_depth==1 and d.native_legality_calls==0

@pytest.mark.skipif(not native_available(),reason='native unavailable')
def test_provider_rejects_other_rules_and_poll_failure_without_mutating_position():
    c,core=root('chess-ep');other,foreign=root('shogi-drop')
    provider=NativeSemanticLegalityProvider.try_create(c,strict=True);saved=core.runtime.position
    with pytest.raises(ValueError,match='source mismatch'):provider.has_legal_action(foreign.runtime.position)
    def interrupted():raise RuntimeError('poll')
    with pytest.raises(RuntimeError,match='poll'):provider.has_legal_action(saved,checkpoint=interrupted)
    assert core.runtime.position is saved and provider.availability_metrics['queries']==0

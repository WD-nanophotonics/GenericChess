"""The root observer must preserve real search work and exception unwinding."""
import time
from dataclasses import replace
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession
from ai_fixtures import build_4x4_rooks
from scripts.leaper_root_cost_observer import RootCostObserver


def test_root_cost_observer_preserves_real_core_work_and_restores_function():
    compiled=build_4x4_rooks();state=GameSession(compiled)
    original=S.negamax;decisions=[];provider=[]
    for observed in (False,True):
        player=AlphaBetaPlayer(compiled,use_disk_cache=False,
            tuning=SearchTuning(use_pvs=True,use_root_tactical=False))
        obs=RootCostObserver(time.perf_counter())
        if observed:
            with obs:
                dec=player.choose_action(state,SearchLimits(max_depth=3,quiescence_max_depth=0,max_nodes=10000))
            assert obs.events and all(e['completed']for e in obs.events)
            assert all(e['raw_return']==-e['root_negated_return']for e in obs.events)
        else:
            dec=player.choose_action(state,SearchLimits(max_depth=3,quiescence_max_depth=0,max_nodes=10000))
        decisions.append(tuple(getattr(dec,k)for k in ['action','score','principal_variation','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','runtime_pushes','runtime_pops']))
        assert S.negamax is original
    assert decisions[0]==decisions[1]


def test_root_cost_observer_keeps_aborted_child_distinct_and_previous_iteration(monkeypatch):
    compiled=build_4x4_rooks();state=GameSession(compiled)
    original=S.negamax
    def actual_abort(*args,**kwargs):
        if args[4]==1 and args[1]>=1:
            raise S.SearchAborted('diagnostic_root_child_abort')
        return original(*args,**kwargs)
    monkeypatch.setattr(S,'negamax',actual_abort)
    player=AlphaBetaPlayer(compiled,use_disk_cache=False,
        tuning=SearchTuning(use_pvs=True,use_root_tactical=False))
    with RootCostObserver(time.perf_counter())as obs:
        decision=player.choose_action(state,SearchLimits(max_depth=4,quiescence_max_depth=0,max_nodes=10000))
    assert S.negamax is actual_abort
    assert decision.completed_depth==1
    assert decision.termination_reason=='diagnostic_root_child_abort'
    assert decision.runtime_pushes==decision.runtime_pops
    failed=[e for e in obs.events if not e['completed']]
    assert len(failed)==1 and failed[0]['raw_return']is None
    assert failed[0]['exception_type']=='SearchAborted'

"""Actual assignment observer must preserve semantics, scopes and unwinding."""
import ast
import pytest
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation import evaluator as EM
from generic_chess.session.session import GameSession
from ai_fixtures import build_4x4_rooks
from scripts import leaper_assignment_dependencies as D


def nested_sample(x):
    def helper():
        return x+1
    return helper()


def test_ast_skips_nested_return_scope_and_is_reversible():
    tree,sites=D.transform(nested_sample,'m')
    assert len(sites)==1
    nested=next(n for n in tree.body[0].body if isinstance(n,ast.FunctionDef))
    assert ast.unparse(nested.body[0])=='return x + 1'


def test_actual_assignment_capture_preserves_result_work_and_eval_counts():
    c=build_4x4_rooks();s=GameSession(c);rows=[];original=(S.negamax,S._quiescence_runtime,S._evaluate,Evaluator._attack_maps,Evaluator._anchor_escape,EM.anchor_square,Evaluator._promotion_bonus)
    for active in (False,True):
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True,use_root_tactical=False))
        if active:
            with D.AssignmentDependencies(depths=(1,2,3))as obs:
                decision=p.choose_action(s,SearchLimits(max_depth=3,quiescence_max_depth=0,max_nodes=10000))
            data=obs.export();assert data['dropped_events']==data['dropped_calls']==0
            assert data['calls']and all(x['completed']for x in data['calls'])
            evaluations=[e for e in data['events']if e['kind']=='EVALUATE'];assert len(evaluations)==decision.evaluation_calls
            for e in evaluations:assert S._bounded_static_score(e['reconstructed_raw_side_to_move'])==e['value']
            assert any(e['kind']=='ASSIGN'and e['names']=='best'and e['expression']=='score'for e in data['events'])
            assert any(e['kind']=='TT_PROBE'for e in data['events'])
        else:
            decision=p.choose_action(s,SearchLimits(max_depth=3,quiescence_max_depth=0,max_nodes=10000))
        rows.append(tuple(getattr(decision,k)for k in ['action','score','principal_variation','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','runtime_pushes','runtime_pops','evaluation_calls']))
        assert original==(S.negamax,S._quiescence_runtime,S._evaluate,Evaluator._attack_maps,Evaluator._anchor_escape,EM.anchor_square,Evaluator._promotion_bonus)
    assert rows[0]==rows[1]


def test_observer_entry_failure_restores_partial_global_installation(monkeypatch):
    original=D.transform
    before=(S.negamax,S._quiescence_runtime,S.noisy_child,S._evaluate)
    def fail_second(function,kind):
        if kind=='q':raise RuntimeError('injected compile failure')
        return original(function,kind)
    monkeypatch.setattr(D,'transform',fail_second)
    with pytest.raises(RuntimeError,match='injected compile failure'):
        with D.AssignmentDependencies():pass
    assert before==(S.negamax,S._quiescence_runtime,S.noisy_child,S._evaluate)
    assert not hasattr(S,'_leaper_dependency')


def test_aborted_call_never_fabricates_numeric_return(monkeypatch):
    original=S._evaluate
    def aborted(*args,**kwargs):
        raise S.SearchAborted('injected_evaluation_abort')
    monkeypatch.setattr(S,'_evaluate',aborted)
    c=build_4x4_rooks();s=GameSession(c)
    p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_root_tactical=False))
    with D.AssignmentDependencies(depths=(1,2))as obs:
        decision=p.choose_action(s,SearchLimits(max_depth=2,quiescence_max_depth=0,max_nodes=10000))
    assert decision.termination_reason=='injected_evaluation_abort'
    assert decision.completed_depth==0
    assert decision.runtime_pushes==decision.runtime_pops
    failed=[c for c in obs.calls if not c['completed']]
    assert failed and all('return_ref'not in c for c in failed)
    assert S._evaluate is aborted

"""Targeted causal event hooks preserve restoration and exact guard checks."""
import pytest
from scripts.leaper_frontier_surgery import FrontierEventReplacement
from generic_chess.ai.alphabeta import search as S


def test_frontier_event_restores_after_no_query_exception():
    original=(S.negamax,S._quiescence_runtime)
    with pytest.raises(RuntimeError):
        with FrontierEventReplacement({}):raise RuntimeError('interrupt beforequery')
    assert original==(S.negamax,S._quiescence_runtime)


def test_frozen_target_requires_full_path_and_window_before_replacement(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(S,'negamax',lambda*a,**k:None)
    monkeypatch.setattr(S,'_quiescence_runtime',lambda*a,**k:-1087)
    ctx=SimpleNamespace(runtime=SimpleNamespace(ply_count=52,position=SimpleNamespace(side_to_move=0)))
    target=dict(target_path=[{'step':'exact'}],expected_absolute_ply=52,expected_actor=0,entry_alpha=-100,entry_beta=100,old_value=-1087,replacement=-1103)
    with FrontierEventReplacement(target)as hook:
        hook.iteration=3;hook.stack=[[{'step':'different'}]]
        assert S._quiescence_runtime(-100,100,3,0,ctx)==-1087
        hook.stack=[[{'step':'exact'}]]
        assert S._quiescence_runtime(-99,100,3,0,ctx)==-1087
        assert not hook.interventions
        assert S._quiescence_runtime(-100,100,3,0,ctx)==-1103
        assert len(hook.interventions)==1
        assert S._quiescence_runtime(-100,100,3,0,ctx)==-1087
        hook.stack=[]

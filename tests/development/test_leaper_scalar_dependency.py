import ast,json
import pytest
from scripts.leaper_scalar_dependency import instrument,ScalarDependencies
from scripts import leaper_design as L
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits


def test_return_wrapper_single_evaluation_and_abort_has_no_false_return():
    source="def q(alpha,beta,ply,qdepth,ctx):\n    return ctx()\n"
    tree,sites=instrument(source,'q');calls=[];events=[]
    ns={'_scalar_return':lambda kind,site,value,env:(events.append((site,value)),value)[1]};exec(compile(tree,'<test>','exec'),ns)
    def once():calls.append(1);return 23
    assert ns['_scalar_q_impl'](0,100,0,0,once)==23 and len(calls)==len(events)==1
    def fail():raise ValueError('abort')
    with pytest.raises(ValueError):ns['_scalar_q_impl'](0,100,0,0,fail)
    assert len(events)==1 and len(sites)==1


def small(*,observer=False,cancel=False):
    from contextlib import nullcontext
    c=L.compile_rule(L.definition(5,7));s=L.GameSession(c);p=AlphaBetaPlayer(c,use_disk_cache=False);seen=[]
    class Cancel:
        def is_cancelled(self):return cancel and bool(seen)
    d=ScalarDependencies(depths=(1,2))if observer else None
    with d if d is not None else nullcontext():r=p.choose_action(s,SearchLimits(max_depth=2,max_time_seconds=10,max_nodes=100000),cancel_token=Cancel(),progress_callback=lambda *a:seen.append(a))
    return r,seen,d


def test_actual_observer_preserves_scores_actions_work_and_runtime():
    old,its,_=small();before=(S.negamax,S._quiescence_runtime,S.noisy_child);new,nits,o=small(observer=True)
    assert (old.action,old.score,old.completed_depth,old.nodes,old.qnodes)==(new.action,new.score,new.completed_depth,new.nodes,new.qnodes)
    assert its==nits and before==(S.negamax,S._quiescence_runtime,S.noisy_child)
    assert o.context is None and not o.stack
    data=o.export();encoded=json.dumps(data);assert '_runtime'not in encoded and 'RuntimeSearchState'not in encoded
    assert [x['iteration']for x in data['records']]==[1,2]
    assert data['records'][-1]['trace']['bound_vs_entry']=='EXACT'


def test_cancel_preserves_completed_fallback_and_restores_functions():
    old,its,_=small(cancel=True);new,nits,o=small(observer=True,cancel=True)
    assert (new.action,new.score,new.completed_depth,new.nodes,new.qnodes,new.termination_reason)==(old.action,old.score,old.completed_depth,old.nodes,old.qnodes,old.termination_reason)
    assert its==nits and not o.stack and o.context is None


def test_nested_helper_return_is_not_a_main_return_site():
    source="def q(alpha,beta,ply,qdepth,ctx):\n    def helper():\n        return ctx()\n    return helper()\n"
    tree,sites=instrument(source,'m');events=[];ns={'_scalar_return':lambda kind,site,value,env:(events.append((kind,value)),value)[1]};exec(compile(tree,'<nested>','exec'),ns)
    assert ns['_scalar_m_impl'](0,100,0,0,lambda:7)==7
    assert len(sites)==len(events)==1

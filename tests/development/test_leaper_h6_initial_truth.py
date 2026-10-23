from copy import deepcopy
from pathlib import Path
import pytest
from scripts.leaper_h6_initial_truth import history_solver,Cap,admit
from scripts.leaper_explorer_truth import load


def test_history_memo_keeps_visited_set_and_remaining_clock():
    solve,count=history_solver([(1,),(2,),(3,),()],{3:0},[0,1,0,1],lambda n:None)
    assert solve(0,3,())==(1,4)
    assert solve(0,2,())==(0,2)
    assert solve(0,3,(2,))==(0,2)


def test_terminal_precedes_repetition_and_clock_in_admitted_core():
    solve,_=history_solver([()],{0:0},[1],lambda n:None)
    assert solve(0,0,(0,))==(1,4)


def test_repetition_cycle_is_draw_not_unbounded_recursion():
    solve,count=history_solver([(1,),(0,)],{},[0,1],lambda n:None)
    assert solve(0,6,())==(0,2)and count()==3


def test_eviction_changes_work_not_values():
    args=([(1,2),(3,),(3,),()],{3:0},[0,1,1,0],lambda n:None)
    a,_=history_solver(*args,cache_entries=1);b,_=history_solver(*args,cache_entries=100)
    assert a(0,6,())==b(0,6,())==(1,4)


def test_hard_recursion_budget_does_not_fill_draw():
    solve,count=history_solver([(1,),(2,),()],{2:0},[0,1,0],lambda n:None,max_calls=1)
    with pytest.raises(Cap,match='CALL_CAP'):solve(0,6,())
    assert count()==1


@pytest.mark.parametrize('field,value',[('max_ply',7),('repetition_limit',3),('stalemate_result','loss')])
def test_template_admission_rejects_changed_history_or_terminal_semantics(field,value):
    d=load('docs/research/data/leaper_h6_initial_truth_20261023/inputs.json.gz')
    f=deepcopy(next(f for f in d['families']if f['status']=='CLOSED'));f['rule'][field]=value
    r=next(r for r in d['rows']if r['family']==f['family'])
    with pytest.raises(ValueError):admit(f,r)

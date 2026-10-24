"""Constructive first-repetition path and cheap-baseline controls."""
from collections import Counter
import pytest
from scripts.leaper_first_repetition_flow import min_first_repetition
from scripts.leaper_repetition_cycle_baseline import repeated_single_cycle

def check_path(edges,terminals,root,counts,q,target,answer):
    assert answer is not None
    walk=answer['walk'];assert walk[0]==root and walk[-1]==target
    assert len(walk)-1==answer['distance'];cc=list(counts)
    for step,(i,j)in enumerate(zip(walk,walk[1:]),1):
        assert j in edges[i] and j not in terminals;cc[j]+=1
        assert (cc[j]>=q)==(step==answer['distance'])
    assert cc[target]==q

def test_legal_q4_predecessors_have_different_first_threshold_ordinals():
    edges=[[1],[0,2],[],[4],[5,0],[6],[0]];terminals={2:0}
    histories=([3,4,5,6,0],[3,4,0,1,0]);distances=[]
    for h in histories:
        assert all(b in edges[a]for a,b in zip(h,h[1:]))
        cc=[h.count(i)for i in range(7)]
        answer=min_first_repetition(edges,terminals,0,cc,4,0,witness=True)
        check_path(edges,terminals,0,cc,4,0,answer);distances.append(answer['distance'])
    assert distances==[6,4]

def test_multiple_cycles_can_be_needed_when_repeated_single_cycle_is_unknown():
    edges=[[1,2,3],[0,4,5],[0,6,7],[0,8],[1],[2],[2],[3],[3],[1]]
    history=[9,1,4,1,5,2,6,2,7,3,8,3,0];cc=[history.count(i)for i in range(10)]
    assert repeated_single_cycle(edges,{},0,cc,4)is None
    answer=min_first_repetition(edges,{},0,cc,4,0,witness=True)
    assert answer['distance']==6;check_path(edges,{},0,cc,4,0,answer)
    # Target is now a different vertex, so the v-to-x path must come first.
    other=min_first_repetition(edges,{},0,cc,4,1,witness=True)
    assert other['distance']==3;check_path(edges,{},0,cc,4,1,other)

def test_static_terminal_precedes_a_repetition_target():
    assert min_first_repetition([[1],[]],{1:0},0,[1,1],2,1)is None
    assert min_first_repetition([[1],[2],[]],{2:None},0,[1,0,0],4,0)is None

def test_current_return_clock_boundary_is_a_separate_test_from_cycle_existence():
    edges=[[1],[2],[3],[0]];cc=[1,0,0,0]
    answer=min_first_repetition(edges,{},0,cc,4,0,witness=True)
    assert answer['distance']==12
    assert answer['distance']>10 and answer['distance']<=12
    check_path(edges,{},0,cc,4,0,answer)
    assert repeated_single_cycle(edges,{},0,cc,4)['distance']==12

@pytest.mark.parametrize('edges,terminals,root,cc,q,target',[
    ([[1],[]],{},0,[1,0],2,0),
    ([[1],[]],{1:0},0,[0,0],2,0),
    ([[1],[]],{1:0},0,[1,2],2,0),
    ([[1],[]],{1:0},1,[1,1],2,0),
])
def test_incomplete_or_nonongoing_contracts_are_rejected(edges,terminals,root,cc,q,target):
    with pytest.raises(ValueError):min_first_repetition(edges,terminals,root,cc,q,target)

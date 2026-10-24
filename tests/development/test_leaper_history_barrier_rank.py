"""Independent count/clock recursion and unsafe-admission controls."""
from functools import lru_cache
from itertools import product,combinations
from fractions import Fraction
import pytest
from scripts.leaper_history_barrier_rank import solve

def exact(edges,sides,ts,root,counts,q,h):
    @lru_cache(None)
    def walk(i,cc,left):
        if i in ts:return 0 if ts[i]is None else 1 if ts[i]==0 else-1
        if left==0 or cc[i]>=q:return 0
        values=[]
        for j in edges[i]:
            child=list(cc);child[j]+=1;values.append(walk(j,tuple(child),left-1))
        return (max if sides[i]==0 else min)(values)
    return walk(root,tuple(counts),h)

def test_current_root_is_playable_but_incoming_third_visit_is_a_draw_barrier():
    edges=[[1],[2],[]];sides=[0,1,0];ts={2:0}
    assert solve(edges,sides,ts,0,{0:3,1:2},limit=4,remaining=2)[0]['value']==1
    assert solve(edges,sides,ts,0,{0:3,1:3},limit=4,remaining=2)[0]['value']==0
    assert solve(edges,sides,ts,0,{0:3,1:2},limit=4,remaining=1)[0]['value']==0

def test_winning_terminal_precedes_repetition_and_clock_draw():
    assert solve([[1],[]],[0,1],{1:0},0,{0:1,1:3},limit=4,remaining=1)[0]['value']==1
    assert solve([[1],[]],[0,1],{1:0},0,{0:1,1:3},limit=4,remaining=0)[0]['value']==0

def test_both_winning_seats_and_draw_cycle_are_distinct():
    assert solve([[1],[2],[]],[0,1,0],{2:1},0,{0:1},limit=4,remaining=2)[0]['value']==-1
    assert solve([[1],[2],[]],[0,1,0],{2:1},0,{0:1},limit=4,remaining=1)[0]['value']==0
    assert solve([[1],[0,2],[]],[0,1,0],{2:0},0,{0:3},limit=4,remaining=8)[0]['value']==0

def test_exact_wdl_reduction_is_not_a_uniform_probability_quotient():
    # Two LEGAL equal-length histories from the same initial vertex3 reach
    # current0 with the same clock and NO incoming count3 barrier.
    # A:3,4,5,6,0. B:3,4,0,1,0. Only count1 versus count2 differs.
    edges=[[1],[0,2],[],[4],[5,0],[6],[0]];sides=[0,1,0,0,1,0,1];ts={2:0}
    histories=([3,4,5,6,0],[3,4,0,1,0]);values=[];probabilities=[]
    for history in histories:
        counts=[history.count(i)for i in range(7)]
        assert all(b in edges[a]for a,b in zip(history,history[1:]))
        result,_=solve(edges,sides,ts,0,dict(enumerate(counts)),limit=4,remaining=8)
        assert result['blocked']==[]
        values.append(result['value'])
        @lru_cache(None)
        def probability(i,cc,h):
            if i in ts:return Fraction(int(ts[i]==0))
            if h==0 or cc[i]>=4:return Fraction(0)
            pp=[]
            for j in edges[i]:
                child=list(cc);child[j]+=1;pp.append(probability(j,tuple(child),h-1))
            # Current seat0's retained policy is its sole legal action.
            return pp[0]if sides[i]==0 else sum(pp,Fraction(0))/len(pp)
        probabilities.append(probability(0,tuple(counts),8))
    assert values==[0,0]and probabilities==[Fraction(7,8),Fraction(3,4)]

@pytest.mark.parametrize('edges,sides,terminals',[
    ([[0]],[0],{}),([[1],[]],[0,1],{}),([[1],[0]],[0,1],{1:0}),
    ([[2],[]],[0,1],{1:0}),
])
def test_incomplete_non_sink_and_non_alternating_graphs_rejected(edges,sides,terminals):
    with pytest.raises(ValueError):solve(edges,sides,terminals,0,{0:1},limit=4,remaining=8)

def test_every_small_alternating_arena_against_explicit_history():
    sides=[0,0,1,1];options=[]
    for side in sides:
        other=[i for i,x in enumerate(sides)if x!=side]
        options.append([('e',list(ee))for k in(1,2)for ee in combinations(other,k)]+[('t',v)for v in(None,0,1)])
    cases=0
    for config in product(*options):
        edges=[v if k=='e'else[]for k,v in config];ts={i:v for i,(k,v)in enumerate(config)if k=='t'}
        for q in(2,3,4):
            @lru_cache(None)
            def walk(i,cc,h):
                if i in ts:return 0 if ts[i]is None else 1 if ts[i]==0 else-1
                if h==0 or cc[i]>=q:return 0
                vv=[]
                for j in edges[i]:
                    child=list(cc);child[j]+=1;vv.append(walk(j,tuple(child),h-1))
                return(max if sides[i]==0 else min)(vv)
            for root in range(4):
                if root in ts:continue
                cache={}
                for cc in product(range(q),repeat=4):
                    if cc[root]==0:continue
                    b=tuple(i for i,n in enumerate(cc)if n==q-1 and i!=root and i not in ts)
                    if b not in cache:cache[b]=solve(edges,sides,ts,root,dict(enumerate(cc)),limit=q,remaining=8)[0]
                    r=cache[b]
                    for h in range(9):
                        actual=r['physical_barrier_value']if r['physical_barrier_value']==0 or r['rank']<=h else 0
                        assert actual==walk(root,cc,h)
                        cases+=1
    assert cases==5925312


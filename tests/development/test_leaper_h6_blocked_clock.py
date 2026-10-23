"""Clock, root-return and terminal precedence controls for the scoped reducer."""
import pytest
from itertools import product
from scripts.leaper_h6_initial_truth import blocked_clock_attractor


def test_unbounded_winning_child_can_be_only_a_repetition_draw_action():
    # Root0 can mate via2. Action0->1 returns to0; in repeat2 it draws,
    # despite1 being a losing unbounded child (it would otherwise return to
    # winning0 and then lose to2). Every action needs the prefix barrier.
    v,values,ranks,edges=blocked_clock_attractor([[1,2],[0],[]],{2:0},[0,1,1],{0})
    assert v(0,6)==1
    assert v(1,5,arriving=True)==0
    assert v(2,5,arriving=True)==1


def test_remaining_clock_and_static_mate_precedence():
    v,*_=blocked_clock_attractor([[1],[2],[3],[]],{3:0},[0,1,0,1],{0,3})
    assert v(0,2)==0
    assert v(0,3)==1
    assert v(3,0,arriving=True)==1


def test_repeated_arrival_is_not_the_same_as_current_root():
    v,*_=blocked_clock_attractor([[1],[2],[]],{2:1},[0,1,0],{0,1})
    assert v(1,4,arriving=True)==0
    assert v(1,4)==-1


def test_local_move_scope_rejects_non_alternating_turns():
    with pytest.raises(ValueError,match='nonalternating'):
        blocked_clock_attractor([[1],[]],{1:0},[0,0],set())


def test_finite_history_lemma_on_all_four_vertex_alternating_games():
    # Exhaustive abstract semantic control, not a new Leaper rule campaign.
    # Each vertex is draw, mate against its actor, or has one of the three
    # nonempty subsets of the opposite side's vertices as legal moves.
    # Literal occurrence counts independently model repeat2 and repeat4.
    sides=[0,1,0,1];options=[];checked=0
    for side in sides:
        choices=tuple(i for i,s in enumerate(sides)if s!=side)
        options.append([('T',None),('T',1-side),('E',choices[:1]),('E',choices[1:]),('E',choices)])
    for declarations in product(*options):
        edges=[value if kind=='E'else()for kind,value in declarations]
        terminals={i:value for i,(kind,value)in enumerate(declarations)if kind=='T'}
        for repeat in(2,4):
            table={}
            def literal(i,remaining,counts):
                key=(i,remaining,counts)
                if key in table:return table[key]
                if i in terminals:
                    w=terminals[i];v=0 if w is None else 1 if w==0 else-1
                elif not remaining or counts[i]>=repeat:v=0
                else:
                    children=[]
                    for j in edges[i]:
                        cc=list(counts);cc[j]+=1
                        children.append(literal(j,remaining-1,tuple(cc)))
                    v=(max if sides[i]==0 else min)(children)
                table[key]=v
                return v
            for i in range(4):
                counts=tuple(int(i==j)for j in range(4));literal(i,6,counts)
            reducers={}
            for (i,remaining,counts),actual in table.items():
                if i in terminals or not remaining or counts[i]>=repeat:continue
                blocked=frozenset(j for j,n in enumerate(counts)if n>=repeat-1)
                if blocked not in reducers:reducers[blocked]=blocked_clock_attractor(edges,terminals,sides,blocked)[0]
                value=reducers[blocked]
                assert value(i,remaining)==actual
                for j in edges[i]:
                    cc=list(counts);cc[j]+=1
                    assert value(j,remaining-1,arriving=True)==table[j,remaining-1,tuple(cc)]
                checked+=1
    assert checked>10000

"""Semantic failures that a future-history projection must prevent."""
from fractions import Fraction as F
import pytest
from scripts.leaper_future_history_cone import future_cones,make_solver

def test_current_repetition_must_be_checked_before_forgetting_the_past():
    # No future return to0 exists. Yet arriving0 with0alreadyseen is terminal.
    edges=[[1],[2],[]];terms={2:0};sides=[0,1,0]
    full=make_solver(edges,sides,terms,2,projected=False)
    small=make_solver(edges,sides,terms,2,projected=True)
    assert future_cones(edges,terms,2)[2][0]&1==0
    assert full[0](0,2,1)==small[0](0,2,1)==(0,(F(0),F(0),F(0),F(1),F(0)))
    # Incorrectly dropping the CURRENT stop flag would invent this win.
    assert small[0](0,2,0)[0]==1

def test_last_ply_repetition_identity_is_needed_for_reason_even_with_same_draw():
    edges=[[1],[0]];sides=[0,1];small=make_solver(edges,sides,{},1,projected=True)
    repeated=small[0](0,1,1<<1);fresh=small[0](0,1,0)
    assert repeated[0]==fresh[0]==0
    assert repeated[1][3]==1 and fresh[1][4]==1
    assert small[1](0,1,1<<1)!=small[1](0,1,0)

def test_static_mate_wins_at_repetition_and_clock_boundary():
    edges=[[1],[]];sides=[0,1];terms={1:0};small=make_solver(edges,sides,terms,1,projected=True)
    assert small[0](1,0,1<<1)==(1,(F(1),F(0),F(0),F(0),F(0)))
    assert small[0](0,1,1<<1)[0]==1

def test_only_future_relevant_memberships_may_be_erased():
    edges=[[1],[2],[],[2]];sides=[0,1,0,1];terms={2:0}
    small=make_solver(edges,sides,terms,2,projected=True)
    assert small[1](0,2,1<<3)==small[1](0,2,0)
    assert small[1](0,2,1<<1)!=small[1](0,2,0)
    assert small[0](0,2,1<<3)[0]==1 and small[0](0,2,1<<1)[0]==0

@pytest.mark.parametrize('edges,terms', [([[1],[]],{}),([[1],[0]],{1:None}),([[2],[]],{1:None})])
def test_partial_or_non_sink_graph_cannot_claim_a_complete_future_cone(edges,terms):
    with pytest.raises(ValueError):future_cones(edges,terms,2)

def test_non_alternating_graph_is_outside_admitted_game_scope():
    with pytest.raises(ValueError):make_solver([[0]],[0],{},2,projected=True)

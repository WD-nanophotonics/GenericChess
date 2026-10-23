from fractions import Fraction as F
import pytest
from scripts.leaper_h6_headroom import evaluate
from scripts.leaper_h6_policy_bounds import policy_values
from scripts.leaper_material_trade_cells import count_box,crossings,examples
from scripts.leaper_twoa_exposure_bounds import first_hit


def panel():
    # Choice between ongoing material(1-B) leading to LOSS, and DRAW-zero.
    edges=[[1,2],[3],[4],[],[]];terms={3:1,4:None};sides=[0,1,1,0,0]
    features=[(1,-1),(1,-1),(0,0),(1,-1),(0,0)]
    return edges,terms,sides,evaluate(edges,terms,sides,features)


def test_terminal_authority_precedes_clock_and_repetition():
    _,_,_,(ended,truth,nominal,decision,calls)=panel()
    assert truth(3,0,1<<3)==-1
    assert truth(4,0,1<<4)==0
    assert truth(0,4,1<<0)==0
    assert nominal(3,0,1<<3,2,F(2))<0


def test_tie_uncertainty_is_not_an_actual_tie_choice():
    _,_,_,(ended,truth,nominal,decision,calls)=panel()
    assert decision(0,4,0,1,F(1,2))['error']==1
    assert decision(0,4,0,1,F(1))['error']==F(1,2)
    assert decision(0,4,0,1,F(2))['error']==0
    assert decision(0,4,0,2,F(1))['error']==0
    with pytest.raises(ValueError):decision(3,4,0,1,F(1))


def test_exact_policy_distribution_and_tie_envelope():
    edges,terms,sides,(ended,truth,nominal,decision,calls)=panel()
    walk,_=policy_values(edges,terms,sides,ended,truth,decision,1,F(1),'UNIFORM')
    dist,lo,hi,regret=walk(0,4,0)
    assert dist==(0,F(1,2),F(1,2))
    assert (lo,hi,regret)==(-1,0,F(1,2))
    good,_=policy_values(edges,terms,sides,ended,truth,decision,1,F(2),'UNIFORM')
    assert good(0,4,0)==((0,1,0),0,0,0)


def test_floor_is_a_fixed_opponent_policy_not_a_label_filter():
    edges=[[1,2],[],[]];terms={1:1,2:None};sides=[1,0,0]
    ended,truth,nominal,decision,_=evaluate(edges,terms,sides,[(1,-1)]*3)
    uniform,_=policy_values(edges,terms,sides,ended,truth,decision,1,F(1),'UNIFORM')
    floor,_=policy_values(edges,terms,sides,ended,truth,decision,1,F(1),'FLOOR')
    assert uniform(0,3,0)[0]==(0,F(1,2),F(1,2))
    assert floor(0,3,0)[0]==(0,0,1)


def test_nonzero_trade_does_not_universally_require_five_actors():
    cases=examples()['cases']
    assert all(not r['nonzero']for r in cases['one_each_split']['positive_crossings'])
    assert any(r['nonzero']and r['B']=='1'for r in cases['two_types_same_owner']['positive_crossings'])
    assert any(r['nonzero']for r in cases['five_actor_split']['positive_crossings'])
    assert not cases['one_kind_split']['positive_crossings']
    assert not cases['two_identical_same_owner']['positive_crossings']
    with pytest.raises(ValueError):count_box([(0,'A',-1)])


def test_shadow_first_hit_respects_absolute_clock_and_mass():
    # At one ply before the clock, a newly arrived target has no decision.
    edges=[[1],[0]]
    assert first_hit(edges,{},0,1,0,{1})['upper']=='0'
    r=first_hit(edges,{},0,2,0,{1})
    assert r['lower']==r['upper']=='1'
    late=first_hit(edges,{},0,2,12,{1})
    assert late['lower']=='0'and late['upper']=='1'
    # Physical terminals stop the shadow process before an event can be hit.
    assert first_hit([[1],[]],{1:0},0,3,0,{1})['upper']=='0'

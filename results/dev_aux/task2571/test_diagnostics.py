"""Meaningful paired/censor controls, including fixed-opponent violation."""
import pytest
from results.dev_aux.task2571.trajectory import compare
from results.dev_aux.task2568.summary import contrast
START='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
def game(moves,color=0,reward=None):return dict(slot=[0,1977,441001,color,'TD','uniform'],initial_record=dict(initial=START,moves=[]),record=dict(initial=START,moves=moves),reward=reward)
def test_white_divergence_negative_outcome_kept():
 a=game(['e2e4'],reward=-1);b=game(['d2d4'],reward=1);r=compare(a,b);assert r['kind']=='CANDIDATE_FIRST_DIVERGENCE'and r['reward_gain']==-2

def test_black_divergence_after_same_foe_move():
 r=compare(game(['e2e4','c7c5'],1,1),game(['e2e4','e7e5'],1,-1));assert r['candidate']==1 and r['common_plies']==1 and r['reward_gain']==2

def test_changed_fixed_foe_is_rejected():
 with pytest.raises(AssertionError,match='Fixedfoe'):compare(game(['e2e4'],1),game(['d2d4'],1))

def test_prefix_censor_is_not_draw_or_move_effect():
 r=compare(game(['e2e4'],reward=None),game(['e2e4','e7e5'],reward=1));assert r['kind']=='PREFIX_ONLY_END_OR_CENSOR'and r['reward_gain']is None

def test_unknown_missing_pair_retains_full_reward_bounds():
 slots=[[0,1977,441001,0,m,'uniform']for m in('TD','initial')];a=game([],reward=1);r=contrast({tuple(slots[0]):a},slots,'TD','initial');assert r['bounds']==[0,2]and r['counts']['missing_pair']==1

def test_actual_draw_is_distinct_from_unknown():
 slots=[[0,1977,441001,0,m,'uniform']for m in('TD','initial')];rr={tuple(slots[0]):game([],reward=0),tuple(slots[1]):game([],reward=None)};assert contrast(rr,slots,'TD','initial')['bounds']==[-1,1];rr[tuple(slots[1])]['reward']=0;assert contrast(rr,slots,'TD','initial')['bounds']==[0,0]

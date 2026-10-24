"""Do not confuse root payoff, shared-action values and new-action support."""
import pytest
from scripts.leaper_structural_counterfactual import classify

K=('K',0,1,None);A=('A',2,3,None);NEW=('A',2,4,None)
def row(keys,values):return dict(action_keys=keys,values=values)

def test_shared_winning_action_can_be_lost_with_root_win_preserved():
    r=classify(row([K,A],[1,1]),row([K,A,NEW],[1,0,1]))
    assert r['root_values']==[1,1]and r['shared_revaluations']==[dict(action=list(A),values=[1,0])]
    assert r['old_action_optimal_membership_changed']==[list(A)]and r['new_optimal_actions']==[list(NEW)]

def test_added_drawing_action_is_not_shared_revaluation_or_new_best_move():
    r=classify(row([K],[1]),row([K,NEW],[1,0]))
    assert r['root_values']==[1,1]and not r['shared_revaluations']and not r['support_changed']
    assert r['added_actions']==[list(NEW)]and r['new_optimal_actions']==[]

def test_removed_physical_action_is_rejected_under_singleton_orbit_addition():
    with pytest.raises(AssertionError):classify(row([K,A],[1,0]),row([K,NEW],[1,0]))

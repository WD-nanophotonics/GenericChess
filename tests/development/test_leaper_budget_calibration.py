from fractions import Fraction as F
from scripts.leaper_budget_calibration import effects, interval_mean


def test_role1_can_gain_while_raw_utility_is_negative():
    # A high-budget role1 loses, but the same role previously lost more often.
    e=effects([F(3,8)]*2,[F(1,2)]*2,[F(1,8)]*2)
    assert e['own0_fixed_low']==[F(1,8)]*2
    assert e['own1_fixed_low']==[F(1,4)]*2
    assert e['balanced']==e['cross_balanced']==[F(3,16)]*2


def test_missing_baseline_does_not_turn_unknown_into_a_gain():
    e=effects([-1,1],[1,1],[-1,-1])
    assert e['own0_fixed_low']==[0,2]
    assert e['own1_fixed_low']==[0,2]
    assert e['balanced']==[0,2]  # Marginals share an unknown baseline.
    assert e['cross_balanced']==[1,1]  # The paired contrast cancels it.


def test_a_negative_role_is_not_hidden_by_positive_mean():
    e=effects([1,1],[0,0],[-1,-1])
    assert e['own0_fixed_low']==[-1,-1]
    assert e['own1_fixed_low']==[2,2]
    assert e['balanced']==[F(1,2)]*2
    assert interval_mean([]) is None

import pytest
from scripts.verify_leaper_real_budget import paired

def row(budget,key,arm,correct=True):return dict(budget=budget,key=key,arm=arm,seconds=1.,caller_seconds=1.2,correct=correct,choice_sensitive=True,node_target_censored=False)

def test_same_history_different_budget_is_not_a_pair():
    a=paired([row('fixed1.5','a','default'),row('balanced50k','a','refined')])
    assert a['fixed1.5']['pairs']==a['balanced50k']['pairs']==0
    assert a['fixed1.5']['unpaired_UNKNOWN']==['a']

def test_paired_regression_not_hidden_by_other_budget_repair():
    a=paired([row('fixed1.5','a','default'),row('fixed1.5','a','refined',False),row('balanced50k','a','default',False),row('balanced50k','a','refined')])
    assert a['fixed1.5']['regressions']==['a']and a['balanced50k']['repairs']==['a']

def test_duplicate_arm_refused():
    with pytest.raises(AssertionError):paired([row('fixed1.5','a','default')]*2)

from fractions import Fraction
import pytest
from scripts.leaper_forecast import ranks,spearman,means
from scripts.leaper_portrait import role_summary

def test_tied_ranks_use_group_average_not_input_order():
    assert ranks([1,1,4,2])==[Fraction(3,2),Fraction(3,2),4,3]
    assert ranks([4,1,2,1])==[4,Fraction(3,2),3,Fraction(3,2)]

def test_exact_monotone_and_constant_negative_controls():
    assert spearman([1,2,3],[6,4,2])==-1
    assert spearman([1,2,3],[2,4,6])==1
    assert spearman([1,1],[1,2]) is None
    with pytest.raises(ValueError):spearman([1],[1,2])

def test_unknown_utility_is_completion_interval_not_draw():
    assert means([{'utility':[-1,1]},{'utility':[1,1]}])==[0,1]
    with pytest.raises(ValueError):means([])

def test_rejected_layout_slot_cannot_be_reported_as_zero_role_mean():
    slots=[{'role':0,'utility':[-1,1],'status':'setup_failed'},
           {'role':1,'utility':[1,1],'status':'finished'}]
    assert role_summary(slots,0)=={'planned':1,'utility_bounds':[-1,1],'mean':None}
    assert role_summary(slots,1)=={'planned':1,'utility_bounds':[1,1],'mean':1}
    assert role_summary(slots,2)=={'planned':0,'utility_bounds':None,'mean':None}

@pytest.mark.parametrize('base,candidate,expected',[
    ([0,0],[-1,1],['-1','1']),
    ([-1,1],[1,1],['0','2']),
])
def test_paired_budget_missing_outcome_preserves_completion_bounds(tmp_path,base,candidate,expected):
    from scripts.leaper_forecast import paired_capacity
    from scripts.research_record import write_record
    dirs=[tmp_path/'candidate',tmp_path/'baseline']
    reg={k:False for k in ('seed','caller_plies','rule_max_ply','repetition_limit','q','forced_check_depth','disk_cache','TT','source_sha256')}
    for d,u in zip(dirs,[candidate,base]):
        d.mkdir();write_record(d/'registration.json',reg)
        write_record(d/'inputs.json',{'worlds':[{'masks':[1,2],'full_rule':'same'}]})
        write_record(d/'results.json',{'status':'CLOSED','slots':[{'slot':0,'world':0,'role':0,'repeat':0,'pair':'AB_RNG','status':'not_started','utility':u}]})
    result=paired_capacity(dirs[0],[dirs[1]])
    assert result['difference_bounds']==expected
    assert result['rows'][0]['full_trajectory_identical'] is None
    write_record(dirs[1]/'inputs.json',{'worlds':[{'masks':[1,2],'full_rule':'different'}]})
    with pytest.raises(AssertionError,match='identical full rules'):paired_capacity(dirs[0],[dirs[1]])

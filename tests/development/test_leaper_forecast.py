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

def test_proposal_keeps_missing_losses_and_conditional_win_lengths(tmp_path):
    from scripts.leaper_forecast import proposal_analysis
    from scripts.leaper_design import sha
    from scripts.research_record import write_record
    write_record(tmp_path/'inputs.json',{'worlds':[{'masks':[1,2],'geometry':[{'mean_empty_board_degree':1}]} ,{'masks':[3,4],'geometry':[{'mean_empty_board_degree':2}]}]})
    reg={'pairs':{'AB_FLOOR':['AB','FLOOR']},'roles':[0,1],'repetitions':1,'planned_games':4,
         'proposal_groups':{'control':[0],'guided':[1]},'input_sha256':sha(tmp_path/'inputs.json')}
    write_record(tmp_path/'registration.json',reg)
    slots=[]
    for w in (0,1):
        for role in (0,1):
            ix=2*w+role;value=1 if w==0 else -1
            s={'slot':ix,'world':w,'pair':'AB_FLOOR','role':role,'repeat':0,'status':'not_started','utility':[-1,1]}
            if role==0:
                s.update(status='finished',utility=[value,value],receipt=f'g{ix}.json')
                write_record(tmp_path/s['receipt'],{**s,'queries':[{'seconds':0.25}]*3,'seconds':1,'final_record':{'actions':[w]}})
            slots.append(s)
    write_record(tmp_path/'results.json',{'status':'CLOSED','slots':slots})
    out=proposal_analysis(tmp_path)
    assert out['primary_guided_minus_control_DIRECT_bounds']==['-2','0']
    assert out['groups']['control']['AB_FLOOR']['conditional_win_mean_plies']=='3'
    assert out['groups']['guided']['AB_FLOOR']['conditional_win_mean_plies'] is None
    assert out['groups']['guided']['AB_FLOOR']['outcomes']=={'-1':1,'UNKNOWN':1}
    slots[-1]['repeat']=1
    write_record(tmp_path/'results.json',{'status':'CLOSED','slots':slots})
    with pytest.raises(AssertionError,match='census'):proposal_analysis(tmp_path)

def test_budget_analysis_binds_actual_actor_and_counts_duplicate_physical_games(tmp_path):
    from scripts.leaper_forecast import budget_analysis
    from scripts.leaper_design import sha
    from scripts.research_record import write_record
    write_record(tmp_path/'inputs.json',{'worlds':[{'world':0,'masks':[1,2]}]})
    reg={'nodes':8,'search_variants':{'HI':{'base':'AB','nodes':16}},'pairs':{'HI_LO':['HI','AB']},
         'roles':[0,1],'repetitions':2,'planned_games':4,'input_sha256':sha(tmp_path/'inputs.json')}
    write_record(tmp_path/'registration.json',reg);slots=[]
    for role in (0,1):
        for rep in (0,1):
            ix=2*role+rep;s={'slot':ix,'world':0,'pair':'HI_LO','role':role,'repeat':rep,'status':'not_started','utility':[-1,1]}
            if role==0:
                s.update(status='finished',utility=[1,1],receipt=f'g{ix}.json')
                q={'actor':0,'policy':'HI','base_policy':'AB','node_budget':16,'seconds':0.25,'root_ply':0,
                   'decision':{'nodes':17,'qnodes':0,'completed_depth':1,'result_source':'main_iteration'}}
                write_record(tmp_path/s['receipt'],{**s,'queries':[q],'seconds':1,'final_record':{'actions':['same deterministic action']}})
            slots.append(s)
    write_record(tmp_path/'results.json',{'status':'CLOSED','seconds':2,'slots':slots})
    out=budget_analysis(tmp_path)
    assert out['pairs']['HI_LO']['utility_bounds']==['0','1']
    assert out['pairs']['HI_LO']['finished']==2 and out['pairs']['HI_LO']['unique_full_records']==1
    assert out['deterministic_repeat_census'][0]['executed']==2
    assert out['deterministic_repeat_census'][0]['unique_full_records']==1
    # The actual inclusive-abort count is reported, not silently clipped to budget.
    assert out['costs_by_budget'][0]['actual_nodes']==34
    from scripts.leaper_design import load
    row=load(tmp_path/'g0.json');row['queries'][0]['node_budget']=8;write_record(tmp_path/'g0.json',row)
    with pytest.raises(AssertionError,match='actor budget'):budget_analysis(tmp_path)

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

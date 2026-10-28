"""Reject policy/resource drift and missing-outcome success claims."""
import copy
import pytest
from scripts.verify_leaper_admitted_extension import service,endpoints,submission
from scripts.verify_leaper_start_admission import rejection_codes
from generic_chess.rules.validation import RuleValidationError,ValidationIssue

def query(on=False):
    return dict(on=on,requested_service_seconds=1.5,limits=dict(max_time_seconds=1.4,max_depth=64,max_nodes=500000,quiescence_max_depth=4,quiescence_hard_max_depth=8),construction_packing_seconds=.1,service_wall_seconds=1.5,timing_eligible=True,actual_tuning=dict(use_root_tactical=True,use_ordered_qsearch_in_check=True,use_one_check_extension=on,require_full_pv=False,stop_after_root_win=False),provider_present=True,provider_delta=dict(availability=dict(declines=0)),decision=dict(pvs_null_window_searches=0,pvs_researches=0,main_extension_max_path=int(on),main_check_extensions=int(on),main_search_max_ply=8 if on else 0,runtime_depth_balanced=True,native_legality_fallbacks=0,native_legality_operational_failures=0,result_source='main_iteration',completed_depth=1,result_ordinary_qdepth=0))

@pytest.mark.parametrize('on',[False,True])
def test_resource_identity_matches_conditional_extension(on):service(query(on))

@pytest.mark.parametrize('defect',['unequal_budget','hidden_pvs','OFF_extended','Q4_on_first_iteration','wrong_extension_flag','construction_outside_budget','unbalanced'])
def test_actual_contract_drift_rejected(defect):
    q=query()
    if defect=='unequal_budget':q['requested_service_seconds']=2
    if defect=='hidden_pvs':q['actual_tuning']['use_pvs']=True
    if defect=='OFF_extended':q['decision']['main_check_extensions']=1
    if defect=='Q4_on_first_iteration':q['decision']['result_ordinary_qdepth']=4
    if defect=='wrong_extension_flag':q['actual_tuning']['use_one_check_extension']=True
    if defect=='construction_outside_budget':q['construction_packing_seconds']=.3
    if defect=='unbalanced':q['decision']['runtime_depth_balanced']=False
    with pytest.raises(AssertionError):service(q)

def games():
    fs=[0]*4+[1]*4+[2]*2+[3]*4+[4]*4+[5]*4+[6]*4+[7]*4
    return [dict(family=f,status='TERMINAL',timing_eligible=True,on_seat=i%2,Core_terminal=dict(winner=None)) for i,f in enumerate(fs)]

def test_one_missing_game_is_unknown_not_draw_or_pass():
    gs=games();gs[0]['status']='NOT_STARTED';r=endpoints(gs)
    assert r['missing']==1 and r['outcomes']=={'DRAW':29}
    assert r['raw_completion_bounds']==[14.5/30,15.5/30]
    assert not r['exploratory_gate_passed']

def test_incomplete_family_has_predeclared_smaller_denominator():
    r=endpoints(games());assert r['families']['2']['planned_games']==2
    assert r['families']['0']['planned_games']==4 and r['equal_family_completion_bounds']==[.5,.5]

def test_raw_and_equal_family_estimates_are_distinct_not_reweighted_acceptance():
    gs=games()
    for g in gs:
        if g['family']==2:g['Core_terminal']['winner']=g['on_seat']
    r=endpoints(gs)
    assert r['ON_points']==16 and r['raw_completion_bounds'][0]==16/30
    assert r['equal_family_completion_bounds'][0]==.5625
    assert not r['exploratory_gate_passed']

def test_post_submit_annotation_is_verified_without_changing_raw():
    raw={'query_id':'q1'};embedded=dict(raw,record_after_sha256='after',root_unchanged=True,pv_legal=True)
    submission(raw,embedded,'after');assert raw=={'query_id':'q1'}
    with pytest.raises(AssertionError):submission(raw,embedded,'tampered')

def test_unrelated_compiler_error_is_not_hidden_by_expected_initial_check():
    a=ValidationIssue('INITIAL_ANCHOR_ATTACKED','initial_position','checked')
    b=ValidationIssue('INITIAL_NO_LEGAL_MOVE','initial_position','no legal action')
    assert rejection_codes(RuleValidationError([a,b]))==[a.code,b.code]
    with pytest.raises(AssertionError):rejection_codes(RuleValidationError([a,ValidationIssue('UNKNOWN_TYPE','piece_types','bad')]))

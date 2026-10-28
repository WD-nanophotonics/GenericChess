"""Fault controls for declared PVS/LMR/budget/provenance and missing outcomes."""
import copy
import pytest
from scripts.verify_leaper_lmr_pilot import service,outcome_bounds
from generic_chess.ai.alphabeta.tuning import SearchTuning
from scripts.research_record import record_value


def sample():
    return dict(requested_service_seconds=1.5,on=True,policy_owned_TT=True,policy_id='late-quiet-nonPV-oneply/v1',
                limits=dict(max_time_seconds=1.3,max_depth=64,max_nodes=500000,quiescence_max_depth=4,quiescence_hard_max_depth=8),construction_packing_seconds=.2,
                actual_tuning=record_value(SearchTuning(use_pvs=True)),service_wall_seconds=1.5,cpu_seconds=1.4,lmr_classification_seconds=.01,timing_eligible=True,
                provider_present=True,provider_delta=dict(availability=dict(declines=0)),lmr=dict(eligible_dispatch_attempts=4,reductions=3,full_depth_researches=1,reduced_fail_low_kept=1),
                decision=dict(runtime_depth_balanced=True,native_legality_fallbacks=0,native_legality_operational_failures=0,main_check_extensions=0,result_source='main_iteration',completed_depth=1,result_ordinary_qdepth=0))


def test_incomplete_probe_is_not_falsely_required_to_finish():
    # One attempted reduction may be interrupted; counters are not all
    # completed-subtree counts. Preserve that valid cancellation contract.
    service(sample())


@pytest.mark.parametrize('fault',['pvs','budget','reserve','policy','counter','provider'])
def test_reject_confound_or_false_accounting(fault):
    q=sample()
    if fault=='pvs':q['actual_tuning']['use_pvs']=False
    elif fault=='budget':q['limits']['max_time_seconds']=1.4
    elif fault=='reserve':q['decision']['result_ordinary_qdepth']=4
    elif fault=='policy':q['policy_id']='existing-PVS/v1'
    elif fault=='counter':q['lmr']['full_depth_researches']=4
    elif fault=='provider':q['provider_delta']['availability']['declines']=1
    with pytest.raises(AssertionError):service(q)


def test_missing_game_is_not_a_draw_or_a_success():
    games=[dict(status='TERMINAL',timing_eligible=True,Core_terminal=dict(winner=None),on_seat=i%2,family=i//2) for i in range(16)]
    games[-1]=dict(status='UNFINISHED',family=7)
    x=outcome_bounds(games)
    assert x['eligible']==15 and x['missing']==1 and x['ON_points']==7.5
    assert x['raw_completion_bounds']==[7.5/16,8.5/16] and not x['gate']

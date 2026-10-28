from copy import deepcopy
import pytest
from scripts.verify_leaper_resource_resolution_control import assert_resource_service

def query(on):
 target=2 if on else 1
 return dict(on=on,requested_service_seconds=target,limits=dict(max_time_seconds=target-.25),construction_packing_seconds=.25,service_wall_seconds=1.5,timing_eligible=on,actual_tuning=dict(use_pvs=False,use_one_check_extension=False,use_root_tactical=True,use_ordered_qsearch_in_check=True,require_full_pv=False,stop_after_root_win=False),decision=dict(result_source='main_iteration',completed_depth=1,result_ordinary_qdepth=0))

def test_same_actual_wall_is_overbudget_at_one_second_but_not_two():
 assert assert_resource_service(query(False)) is False
 assert assert_resource_service(query(True),qualification=True) is True
 with pytest.raises(AssertionError):assert_resource_service(query(False),qualification=True)

def test_resource_on_label_does_not_authorize_an_algorithm_switch():
 q=query(True);q['actual_tuning']['use_one_check_extension']=True
 with pytest.raises(AssertionError):assert_resource_service(q)
 q=query(True);q['actual_tuning']['use_pvs']=True
 with pytest.raises(AssertionError):assert_resource_service(q)

def test_requested_q4_is_not_evidence_first_retained_iteration_used_q4():
 q=query(True);q['decision']['result_ordinary_qdepth']=4
 with pytest.raises(AssertionError):assert_resource_service(q)
 q['decision']['completed_depth']=2
 assert assert_resource_service(q) is True

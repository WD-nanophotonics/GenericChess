import copy
import pytest
from scripts.verify_leaper_first_ordinary_return import stage_contract

def row(arm='refined'):
    return dict(arm=arm,seconds=.2,iterations=[dict(depth=1,ordinary_qdepth=0,elapsed=.01,score=4,action='a'),dict(depth=1 if arm=='refined'else 2,ordinary_qdepth=4,elapsed=.1,score=5,action='b')],decision=dict(result_source='main_iteration',completed_depth=1 if arm=='refined'else 2,score=5,action='b'))

def test_actual_return_must_match_completed_stage():
    r=row();assert stage_contract(r)
    r['decision']['action']='a'
    with pytest.raises(AssertionError):stage_contract(r)

def test_repeated_d1_is_not_d2():
    r=row();r['iterations'][1]['depth']=2
    with pytest.raises(AssertionError):stage_contract(r)
    assert stage_contract(row('default'))

def test_incomplete_goal_is_unknown_with_legal_fallback():
    r=row();r['iterations']=r['iterations'][:1];r['decision'].update(action='a',score=4,completed_depth=1)
    assert not stage_contract(r)

def test_forged_return_time_rejected():
    r=row();r['seconds']=.05
    with pytest.raises(AssertionError):stage_contract(r)


def test_completed_root_win_source_is_not_forged_as_last_uniform_iteration():
    r=row();r['decision'].update(result_source='completed_root_win',action='proved_win',score=999999997)
    assert stage_contract(r)

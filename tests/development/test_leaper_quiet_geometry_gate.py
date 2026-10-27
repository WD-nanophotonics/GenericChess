"""Observed short-call CPU resolution must not become zero-cost success."""
from scripts.leaper_quiet_geometry_gate import summarize


def rows():
    return [{'slot':4*i+j,'world':i,'on':j in (1,2),'status':'RETURNED',
             'qualification':'PASS','wall_seconds':.02,'cpu_seconds':.015625,
             'decision':{'quiet_geometry_reorders':1 if j in (1,2) else 0}}
            for i in range(10) for j in range(4)]


def test_zero_cpu_pair_is_unknown_not_a_pass_or_division_failure():
    data=rows()
    for r in data[32:36]:r['cpu_seconds']=0
    result=summarize(data)
    assert result['status']=='STOP_NO_GAMES'
    assert result['reason']=='unresolved_timing_resolution'
    assert result['family_cpu_ratios'][8] is None
    assert result['original_calls']==result['qualified_calls']==40
    assert result['new_games']==0


def test_missing_slot_stays_fixed_denominator_and_cannot_pass():
    data=rows();data[-1]={'slot':39,'world':9,'on':False,'status':'NOT_RUN'}
    result=summarize(data)
    assert result['status']=='STOP_NO_GAMES' and result['not_run']==1
    assert result['qualified_calls']==39 and result['new_games']==0

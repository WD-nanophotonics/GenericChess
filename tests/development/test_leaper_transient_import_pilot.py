"""Frozen eligibility must not turn censored work into speed evidence."""
from copy import deepcopy
from scripts.leaper_transient_import_pilot import analyze,signature,stop
from datetime import datetime,timezone

def fixture():
    return [dict(slot=4*i+j,case_id=str(i),depth=d,on=j in (1,2),status='RETURNED',complete=True,decision={'value':3,'nodes':10,'elapsed_seconds':j},outer_seconds=2 if j in (1,2) else 3,cpu_seconds=1) for i,d in enumerate((6,8)) for j in range(4)]

def test_incomplete_or_different_work_is_not_a_speed_pair():
    rows=fixture();assert analyze(rows)['6']['eligible_root_groups']==1
    rows[1]['complete']=False
    assert analyze(rows)['6']['wall_ratio'] is None
    rows=fixture();rows[2]['decision']['nodes']=11
    assert analyze(rows)['6']['eligible_root_groups']==0
    rows=fixture();rows[3]['decision']['value']=-3
    assert analyze(rows)['6']['eligible_root_groups']==0

def test_zero_cpu_resolution_is_unknown_and_original_work_is_retained():
    rows=fixture()
    for row in rows:row['cpu_seconds']=0
    before=deepcopy(rows);r=analyze(rows)
    assert r['6']['wall_ratio']==2/3 and r['6']['cpu_ratio'] is None
    assert rows==before and r['counts']['RETURNED']==8

def test_dispatch_requires_inflight_and_whole_delivery_reserve(monkeypatch):
    import scripts.leaper_transient_import_pilot as pilot
    monkeypatch.setattr(pilot,'read_json',lambda _: {})
    plan=dict(call_seconds=20,batch_seconds=2100,single_run_origin=datetime.now(timezone.utc).isoformat(),cap_minutes=95,whole_delivery_reserve_seconds=600)
    monkeypatch.setattr(pilot.time,'perf_counter',lambda:2080)
    assert stop(plan,0)=='batch_reserve'
    monkeypatch.setattr(pilot.time,'perf_counter',lambda:0)
    plan['cap_minutes']=10
    assert stop(plan,0)=='whole_delivery_reserve'

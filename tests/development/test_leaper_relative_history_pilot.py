"""Saved-game endpoint authority and cancellation admission controls."""
from scripts.leaper_relative_history_pilot import point,stop_reason
from datetime import datetime,timezone,timedelta
import pytest


def test_only_core_terminal_games_supply_points():
    assert point({'status':'NOT_STARTED'}) is None
    assert point({'status':'ONGOING'}) is None
    assert point({'status':'TERMINAL','on_seat':0,'Core_terminal':{'winner':0,'status':'checkmate'}})==1
    assert point({'status':'TERMINAL','on_seat':1,'Core_terminal':{'winner':0,'status':'checkmate'}})==0
    assert point({'status':'TERMINAL','on_seat':0,'Core_terminal':{'winner':None,'status':'repetition'}})==.5
    with pytest.raises(AssertionError):point({'status':'TERMINAL','on_seat':0,'Core_terminal':{'winner':None,'status':'ongoing'}})


def test_inflight_and_delivery_reserve_cannot_dispatch_to_the_last_second(monkeypatch):
    import scripts.leaper_relative_history_pilot as pilot
    monkeypatch.setattr(pilot,'read_json',lambda _: {})
    plan={'started_at':datetime.now(timezone.utc).isoformat(),'single_run_cap_minutes':110,'delivery_reserve_seconds':900,'game_batch_seconds':3900}
    monkeypatch.setattr(pilot.time,'perf_counter',lambda:3899)
    assert stop_reason(plan,0)=='game_batch_inflight_reserve'
    monkeypatch.setattr(pilot.time,'perf_counter',lambda:3890)
    assert stop_reason(plan,0) is None
    monkeypatch.setattr(pilot,'read_json',lambda _:{'user_paused':True})
    assert stop_reason(plan,0)=='scoped_stop'


def test_zero_length_utc_interval_is_preserved_without_effective_credit(tmp_path,monkeypatch):
    import scripts.leaper_relative_history_pilot as pilot
    def forbidden(*_):raise AssertionError('zero duration must not reach ledger')
    monkeypatch.setattr(pilot.ledger,'record_work',forbidden)
    t=datetime.now(timezone.utc).isoformat()
    pilot.record_interval(t,t,'validation','sub-resolution verification',tmp_path)
    import json
    saved=json.loads((tmp_path/'unverified-clock-intervals.json').read_text(encoding='utf-8'))
    assert saved['intervals'][0]['effective_credit']==0


def test_real_ledger_identity_failure_is_not_swallowed(tmp_path,monkeypatch):
    import scripts.leaper_relative_history_pilot as pilot
    from tools.local_agent.common import LocalFlowError
    def fail(*_):raise LocalFlowError('wrong active owner')
    monkeypatch.setattr(pilot.ledger,'record_work',fail)
    end=datetime.now(timezone.utc)-timedelta(seconds=1)
    with pytest.raises(LocalFlowError,match='wrong active owner'):
        pilot.record_interval((end-timedelta(seconds=1)).isoformat(),end.isoformat(),'research','real interval',tmp_path)

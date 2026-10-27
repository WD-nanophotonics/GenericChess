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

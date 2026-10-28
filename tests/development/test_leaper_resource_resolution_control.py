from pathlib import Path
import json
from types import SimpleNamespace
import pytest
from scripts import leaper_resource_resolution_control as p


def test_all_three_scoped_stop_sources_block_dispatch(monkeypatch):
 for source in ('rollout.json','advisor.json','slack.json'):
  monkeypatch.setattr(p,'read_json',lambda name,source=source: {'research_stopped':True} if Path(name).name==source else {})
  assert p.admission({},0,100,1)=='scoped_stop'


def test_equal_utc_interval_preserved_without_fake_credit(tmp_path,monkeypatch):
 monkeypatch.setattr(p.session,'record_work',lambda *args:pytest.fail('zero interval must not be credited'))
 p.record_interval('2026-10-28T00:00:00+00:00','2026-10-28T00:00:00+00:00','validation','observed subresolution operation',tmp_path)
 assert p.read_json(tmp_path/'unverified-clock-intervals.json')['intervals'][0]['credited_seconds']==0


def test_player_construction_is_inside_service_deadline(tmp_path,monkeypatch):
 clock=[0.0];monkeypatch.setattr(p.time,'perf_counter',lambda:clock[0])
 class SlowConstruct:
  def __init__(self,*args,**kw):
   clock[0]+=2;self._tuning=kw['tuning'];self.native_legality_provider=None
  def choose_action(self,*args,**kw):pytest.fail('no search after construction exhausts service')
 monkeypatch.setattr(p,'AlphaBetaPlayer',SlowConstruct)
 root=SimpleNamespace(to_record=lambda:{'immutable':'root'})
 with pytest.raises(AssertionError,match='exhausted service'):
  p.choose(None,root,{},0,True,1,'controlled',tmp_path,64)
 failure=p.read_json(tmp_path/'failure-controlled.json')
 assert failure['wall']==2 and failure['error_type']=='AssertionError'

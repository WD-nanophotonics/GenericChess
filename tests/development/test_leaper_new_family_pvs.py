from pathlib import Path
import json
from types import SimpleNamespace
import pytest
from scripts import leaper_new_family_pvs as p


def test_frozen_metadata_not_outcome_selected_and_layouts_stay_complete(tmp_path):
 out=tmp_path/'prepared';p.prepare(out);data=p.read_json(out/'inputs.json');assert len(data['rows'])==12
 assert len({r['fingerprint'] for r in data['rows']})==12
 for r in data['rows']:
  w=r['RuleSet'];assert w['board_size']==7 and w['max_ply']==128 and w['repetition_limit']==4 and r['record']['actions']==[]
  board=w['initial_position'];assert sum(x is not None for row in board for x in row)==18
  for y,row in enumerate(board):
   for x,piece in enumerate(row):
    if piece:
     other=board[6-y][6-x];assert other['owner']==1-piece['owner'] and other['current_type_id']==piece['current_type_id']


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


def test_depth_zero_is_not_silently_promoted_to_completed_depth():
 q=dict(decision=dict(completed_depth=0,result_source='legal_fallback',score=0))
 with pytest.raises(AssertionError,match='neither completeD2'):
  p.accept_qualification(q,None,{})
 assert p.accept_qualification(dict(decision=dict(completed_depth=2)),None,{})=='completed_D2'

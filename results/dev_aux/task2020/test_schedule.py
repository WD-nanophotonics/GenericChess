import json
import pytest
from results.dev_aux.task2020.campaign import scheduled_slots,CampaignCap

def plan():return dict(prices=[360,720,1440],train_opponent_R=[1260]*8)

def test_train_lock_precedes_crossed_dev_and_reports_ties(tmp_path):
 rows=[]
 for slot in scheduled_slots(plan(),rows,tmp_path,lambda:False):
  if slot['phase']=='DEV':assert (tmp_path/'FULL-lock-before-dev.json').exists()
  rows.append(dict(slot,outcome='WIN' if slot['B'] in (1440,) else 'DRAW',finite_event_score=1 if slot['B'] in (1440,) else 0,seconds=.01))
 lock=json.loads((tmp_path/'FULL-lock-before-dev.json').read_text())
 assert lock['selected_B']==1440 and lock['all_maximizers']==[1440]
 assert len(rows)==144 and len({(x['family'],x['candidate_side'],x['B'],x['opponent_B']) for x in rows})==144
 assert {(x['family'],x['candidate_side'],x['B'],x['opponent_B']) for x in rows[:48]}=={(f,s,r,720) for f in range(8) for s in (0,1) for r in plan()['prices']}
 assert {(x['family'],x['candidate_side'],x['B'],x['opponent_B']) for x in rows[48:]}=={(f,s,r,o) for f in range(8,16) for s in (0,1) for r in (720,1440) for o in (360,720,1440)}

def test_incomplete_outcome_blocks_selector(tmp_path):
 rows=[];g=scheduled_slots(plan(),rows,tmp_path,lambda:False);slot=next(g)
 rows.append(dict(slot,outcome='UNKNOWN',finite_event_score=None,seconds=.01))
 with pytest.raises(CampaignCap):next(g)
 assert not list(tmp_path.iterdir())

def test_cap_blocks_selector(tmp_path):
 with pytest.raises(CampaignCap):next(scheduled_slots(plan(),[],tmp_path,lambda:True))
 assert not list(tmp_path.iterdir())

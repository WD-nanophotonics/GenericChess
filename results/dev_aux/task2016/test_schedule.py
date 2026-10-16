import json
import pytest
from results.dev_aux.task2016.campaign import scheduled_slots,CampaignCap

def plan():return dict(prices=[360,720,1440,2880],train_opponent_R=[360,720,1440,2880]*4)

def test_train_lock_precedes_crossed_dev_and_reports_ties(tmp_path):
 rows=[]
 for slot in scheduled_slots(plan(),rows,tmp_path,lambda:False):
  if slot['phase']=='DEV':assert (tmp_path/'FULL-lock-before-dev.json').exists()
  rows.append(dict(slot,outcome='WIN' if slot['R'] in (1440,2880) else 'DRAW',finite_event_score=1 if slot['R'] in (1440,2880) else 0,seconds=.01))
 lock=json.loads((tmp_path/'FULL-lock-before-dev.json').read_text())
 assert lock['selected_R']==1440 and lock['all_maximizers']==[1440,2880]
 assert len(rows)==512 and len({(x['family'],x['candidate_side'],x['R'],x['opponent_R']) for x in rows})==512
 assert {(x['family'],x['candidate_side'],x['R'],x['opponent_R']) for x in rows[:128]}=={(f,s,r,plan()['train_opponent_R'][f]) for f in range(16) for s in (0,1) for r in plan()['prices']}
 assert {(x['family'],x['candidate_side'],x['R'],x['opponent_R']) for x in rows[128:]}=={(f,s,r,o) for f in range(16,32) for s in (0,1) for r in (720,1440,2520) for o in (360,720,1440,2880)}

def test_incomplete_outcome_blocks_selector(tmp_path):
 rows=[];g=scheduled_slots(plan(),rows,tmp_path,lambda:False);slot=next(g)
 rows.append(dict(slot,outcome='UNKNOWN',finite_event_score=None,seconds=.01))
 with pytest.raises(CampaignCap):next(g)
 assert not list(tmp_path.iterdir())

def test_cap_blocks_selector(tmp_path):
 with pytest.raises(CampaignCap):next(scheduled_slots(plan(),[],tmp_path,lambda:True))
 assert not list(tmp_path.iterdir())

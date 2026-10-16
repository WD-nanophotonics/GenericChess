import json
import pytest
from results.dev_aux.task2055.campaign import scheduled_slots,CampaignCap

def plan():return dict(prices=[360,720,1440],R_anchors=[1260,2880],interpretation='sameBinteractionotherwise selected-policygains')

def test_both_locks_precede_dev_and_distinct_selectors(tmp_path):
 rows=[]
 for x in scheduled_slots(plan(),rows,tmp_path,lambda:False):
  if x['phase']=='DEV':assert (tmp_path/'FULL-lock-before-dev.json').exists()
  best=360 if x['R']==1260 else 1440
  score=int(x['B']==best)
  rows.append(dict(x,outcome='WIN' if score else 'DRAW',finite_event_score=score,seconds=.01))
 lock=json.loads((tmp_path/'FULL-lock-before-dev.json').read_text())
 assert lock['anchors']['1260']['selected_B']==360 and lock['anchors']['2880']['selected_B']==1440
 assert len(rows)==288 and len({(x['family'],x['candidate_side'],x['R'],x['B'],x['opponent_B']) for x in rows})==288
 assert len(rows[:96])==96 and all(x['family']<8 and x['opponent_R']==1260 and x['opponent_B']==720 for x in rows[:96])
 assert all(x['family']>=8 and x['opponent_R']==1260 for x in rows[96:])
 assert {x['B'] for x in rows[96:] if x['R']==1260}=={360,720}
 assert {x['B'] for x in rows[96:] if x['R']==2880}=={720,1440}

def test_ties_preserved_and_baseline_deduplicated(tmp_path):
 rows=[]
 for x in scheduled_slots(plan(),rows,tmp_path,lambda:False):
  score=int(x['R']==2880 and x['B']==720)
  rows.append(dict(x,outcome='WIN' if score else 'DRAW',finite_event_score=score,seconds=.01))
 lock=json.loads((tmp_path/'FULL-lock-before-dev.json').read_text())
 assert lock['anchors']['1260']['all_maximizers']==[360,720,1440]
 assert lock['anchors']['1260']['selected_B']==360 and lock['anchors']['2880']['selected_B']==720
 assert len(rows)==240

def test_unknown_and_cap_never_select(tmp_path):
 rows=[];g=scheduled_slots(plan(),rows,tmp_path,lambda:False);x=next(g)
 rows.append(dict(x,outcome='UNKNOWN',finite_event_score=None,seconds=.1))
 with pytest.raises(CampaignCap):next(g)
 with pytest.raises(CampaignCap):next(scheduled_slots(plan(),[],tmp_path,lambda:True))
 assert not list(tmp_path.iterdir())

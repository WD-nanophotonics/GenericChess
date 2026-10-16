"""Independent TRAIN-lock audit must reject tampering; no real search."""
import json
import pytest
from results.dev_aux.task1997.campaign import scheduled_slots
from results.dev_aux.task1998 import audit

def test_training_audit_reconstructs_and_rejects_changed_lock(tmp_path,monkeypatch):
 p=dict(prices=[180,360,540,720,900,1080,1260,1440,1800,2160,2520,2880,3600],train_opponent_R=[360,720,1440,2880]*8,opponent_cached=True,opponent_proof_nodes=1024)
 rows=[]
 for s in scheduled_slots(p,rows,tmp_path,lambda:False):
  if s['phase']=='DEV':break
  f,r=s['family'],s['R']
  value=(1 if r==360 else -1 if r==180 else 0)if f<4 else(1 if r==180 else -1 if r==360 else 0)
  rows.append(dict(s,finite_event_score=value,seconds=.01))
 assert len(rows)==832
 monkeypatch.setattr(audit,'ROOT',tmp_path)
 result=audit.training(rows,p);assert result['selected_R']==180 and result['race_R']!=180
 lock=tmp_path/'FULL-lock-before-dev.json';data=json.loads(lock.read_text());data['selected_R']=720;lock.write_text(json.dumps(data))
 with pytest.raises(AssertionError):audit.training(rows,p)

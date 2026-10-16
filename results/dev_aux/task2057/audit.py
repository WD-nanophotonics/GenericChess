"""Independent source/schedule/selector/common-B estimand and physical replay."""
from pathlib import Path
from collections import Counter
import json,hashlib,itertools
from results.dev_aux.task2057.physical_audit import audit,read,lines
from results.dev_aux.task1998.audit import ci
ROOT=Path('results/dev_aux/task2055');OUT=Path('results/dev_aux/task2057')
def run():
 p=read(ROOT/'run-plan.json');physical=audit(ROOT);rows=lines(ROOT/'games.jsonl');q=read(ROOT/'qualification.json');assert len(q['perfts'])==96 and q['native_search_go']==0 and q['source_unchanged'];assert {(e['family'],e['R'],e['B'])for e in q['perfts']}==set(itertools.product(range(16),(1260,2880),(360,720,1440)))
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 result=dict(status='PARTIAL_RETAINED'if not physical['full_study_complete']else'PASS_COMPLETE_FROZEN_TWO_ANCHOR_PILOT',physical=physical,qualification_perfts=96)
 if len(rows)>=96:
  train=rows[:96];cells={(g['family'],g['candidate_side'],g['R'],g['B']):g for g in train};assert len(cells)==96 and set(cells)==set(itertools.product(range(8),(0,1),(1260,2880),(360,720,1440)));assert all(g['phase']=='TRAIN'and g['opponent_R']==1260 and g['opponent_B']==720 for g in train)
  lock=read(ROOT/'FULL-lock-before-dev.json');assert lock['physical_games']==96
  training={};contrasts={}
  for r in p['R_anchors']:
   scores={b:sum(g['finite_event_score']for g in train if g['R']==r and g['B']==b)for b in p['prices']};maximizers=sorted(b for b in scores if scores[b]==max(scores.values()));l=lock['anchors'][str(r)];assert l['scores']=={str(k):v for k,v in scores.items()}and l['all_maximizers']==maximizers and l['selected_B']==maximizers[0]
   training[r]=dict(scores=scores,selected_B=l['selected_B'],all_maximizers=maximizers,nonflat_families=sum(len({sum(cells[f,s,r,b]['finite_event_score']for s in(0,1))for b in p['prices']})>1 for f in range(8)))
  for b in (360,1440):
   ds=[sum(cells[f,s,2880,b]['finite_event_score']-cells[f,s,2880,720]['finite_event_score']-cells[f,s,1260,b]['finite_event_score']+cells[f,s,1260,720]['finite_event_score']for s in(0,1))/2 for f in range(8)]
   contrasts[b]=dict(mean=sum(ds)/8,family_deltas=ds,nonzero_families=sum(x!=0 for x in ds),largest_absolute_family=max(abs(x)for x in ds),sum_absolute_family=sum(abs(x)for x in ds),bootstrap8family_interval=ci(ds,20261016702057+b),scope='COMMON-B TRAINexplorationonly, notDEVvalidation')
  result['TRAIN']=training;result['common_B_TRAIN_interaction']=contrasts
  if physical['full_study_complete']:
   dev=rows[96:];cells={(g['family'],g['candidate_side'],g['R'],g['B'],g['opponent_B']):g for g in dev};assert len(cells)==len(dev);expected={(f,s,r,b,o)for f in range(8,16)for s in(0,1)for r in p['R_anchors']for b in{720,lock['anchors'][str(r)]['selected_B']}for o in(360,720,1440)};assert set(cells)==expected and all(g['phase']=='DEV'and g['opponent_R']==1260 for g in dev)
   gains={}
   for r in p['R_anchors']:
    best=lock['anchors'][str(r)]['selected_B'];ds=[sum(cells[f,s,r,best,o]['finite_event_score']-cells[f,s,r,720,o]['finite_event_score']for s in(0,1)for o in(360,720,1440))/6 for f in range(8,16)]
    gains[r]=dict(selected_B=best,mean=sum(ds)/8,family_deltas=ds,bootstrap8family_interval=ci(ds,20261016702057+r),outcomes={b:dict(Counter(cells[f,s,r,b,o]['outcome']for f in range(8,16)for s in(0,1)for o in(360,720,1440)))for b in sorted({720,best})},per_opponent={o:sum(cells[f,s,r,best,o]['finite_event_score']-cells[f,s,r,720,o]['finite_event_score']for f in range(8,16)for s in(0,1))/16 for o in(360,720,1440)})
   diff=[a-b for a,b in zip(gains[2880]['family_deltas'],gains[1260]['family_deltas'])];same=lock['anchors']['1260']['selected_B']==lock['anchors']['2880']['selected_B']!=720
   result['DEV']=gains;result['DEV_gain_difference']=dict(name='common_selected_B_interaction'if same else'selected_policy_gain_difference_NOT_pure_interaction',mean=sum(diff)/8,family_deltas=diff,bootstrap8family_interval=ci(diff,20261016702058))
 events=lines(ROOT/'run/transport.jsonl');profile=None;cleared=False;profiles=set();intents=0
 for e in events:
  if e['event']=='PROFILE':
   profile=e['values'];r,n,b,pawn=profile;profiles.add(tuple(profile));assert f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}'in e['ack'];cleared=False
  elif e['event']=='CLEAR':assert profile==e['values'];cleared=True
  elif e['event']=='INTENT':assert profile==e['R']and cleared;cleared=False;intents+=1
 assert intents==physical['actual_native'];result['profile_ack_variants']=len(profiles);result['recorded_game_seconds']=sum(g['seconds']for g in rows)
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='physical'}))
if __name__=='__main__':run()

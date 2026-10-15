"""TRAIN-only price stability, fixed equal opponent weighting, no DEV reads."""
from pathlib import Path
from collections import Counter
import json,random,hashlib
OUT=Path('results/dev_aux/task1982');ROOT=Path('results/dev_aux/task1979')
def cohort(index):
 folder=ROOT/f'cohort{index}';lock=json.loads((folder/'FULL-lock-before-dev.json').read_text());p=json.loads((folder/'run-plan.json').read_text())
 rows=[]
 with (folder/'games.jsonl').open(encoding='utf-8') as f:
  for i in range(416):
   x=json.loads(next(f));assert x['phase']!='DEV';rows.append(x)
 assert len(rows)==416
 grid=p['prices'];groups={o:[f for f in range(16) if p['train_opponent_R'][f]==o] for o in (360,720,1440,2880)};assert all(len(g)==4 for g in groups.values())
 score={r:{f:sum(x['finite_event_score'] for x in rows if x['family']==f and x['R']==r)/2 for f in range(16)} for r in grid}
 best=min(grid,key=lambda r:(-sum(score[r].values()),r));assert best==lock['selected_R']
 counts=Counter();rng=random.Random(20261016661982+index)
 for b in range(10000):
  sample=[rng.choice(group) for group in groups.values() for _ in range(4)]
  chosen=min(grid,key=lambda r:(-sum(score[r][f] for f in sample),r));counts[chosen]+=1
 lofo=[]
 for omitted in range(16):
  def objective(r):return sum(sum(score[r][f] for f in fs if f!=omitted)/sum(f!=omitted for f in fs) for fs in groups.values())/4
  chosen=min(grid,key=lambda r:(-objective(r),r));lofo.append(dict(omitted=omitted,selected_R=chosen,ratio=chosen/720))
 peropp={o:dict(best_R=min(grid,key=lambda r:(-sum(score[r][f] for f in fs),r)),scores={r:sum(score[r][f] for f in fs)/4 for r in grid}) for o,fs in groups.items()}
 return dict(cohort=index,selected_R=best,ratio=best/720,nonflat_families=sum(len({score[r][f] for r in grid})>1 for f in range(16)),bootstrap10000_stratified_opponent_selection=dict(counts),lofo_equalnu=lofo,peropponent_TRAIN_description=peropp,outcomes_by_price={r:dict(Counter(x['outcome'] for x in rows if x['R']==r)) for r in grid},source='Exactly first416immutableTRAINrows and FULLlock; no DEV row or labels read. Opponent-stratified resampling and LOFO preserve .25 opponent weight. Resampling existing table is not new learning runs or prospective replication.')
def main():
 OUT.mkdir(exist_ok=True);result=dict(status='PASS_TRAIN_ONLY',cohorts=[cohort(i) for i in (0,1)],no_DEV_read=True)
 with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':main()

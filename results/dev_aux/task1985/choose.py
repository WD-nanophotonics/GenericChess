"""Pool two immutable TRAIN grids only. Never read DEV or choose an opponent weight."""
from pathlib import Path
from collections import Counter
import json,hashlib
OUT=Path('results/dev_aux/task1985')
def run():
 scores={};source=[];seed_prices=[];outcomes={}
 for i in (0,1):
  root=Path('results/dev_aux/task1979')/f'cohort{i}';p=json.loads((root/'run-plan.json').read_text());lock=json.loads((root/'FULL-lock-before-dev.json').read_text());rows=[]
  with (root/'games.jsonl').open(encoding='utf-8') as f:
   for _ in range(416):rows.append(json.loads(next(f)))
  assert len({(x['family'],x['candidate_side'],x['R']) for x in rows})==416 and all(x['phase'] in ('RACE','CONTROL') for x in rows)
  assert Counter(p['train_opponent_R'])=={360:4,720:4,1440:4,2880:4}
  local={r:sum(x['finite_event_score'] for x in rows if x['R']==r) for r in p['prices']};assert local=={int(k):v for k,v in lock['scores'].items()}
  assert min(local,key=lambda r:(-local[r],r))==lock['selected_R'];seed_prices.append(lock['selected_R'])
  for r,v in local.items():scores[r]=scores.get(r,0)+v;outcomes.setdefault(r,Counter()).update(x['outcome'] for x in rows if x['R']==r)
  prefix=b'\n'.join(json.dumps(x,sort_keys=True).encode() for x in rows);source.append(dict(cohort=i,rows=416,canonicalTRAINprefix_sha=hashlib.sha256(prefix).hexdigest(),lock_sha=hashlib.sha256((root/'FULL-lock-before-dev.json').read_bytes()).hexdigest()))
 best=min(scores,key=lambda r:(-scores[r],r));prices=sorted({720,best,*seed_prices})
 result=dict(status='LOCKED_BEFORE_NEW_INPUTS_OR_GAMES',selected_R=best,ratio=best/720,empirical_best_set=[r for r in sorted(scores) if scores[r]==scores[best]],scores=scores,outcomes={r:dict(v) for r,v in outcomes.items()},seed_selected_R=seed_prices,confirmation_prices=prices,maximum_new_games=32*4*2*len(prices),source=source,no_DEV_read=True,scope='832already-paid TRAINgames /32families/8peropponent. Fixed pooled actualW-L/numericascendingtie rule. Reuses two priorlearner datasets, notnewtrainingreplicate. NEW independentconfirmation required; if allpricesidentical skip uninformative games.')
 with (OUT/'selection.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ('outcomes','source')}))
if __name__=='__main__':run()

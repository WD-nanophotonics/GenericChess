"""Frozen finite-grid selection: actual rule W-L, censored slots remain intervals."""
from pathlib import Path
import json,hashlib,datetime
from collections import Counter
OUT=Path('results/dev_aux/task2444')
def select():
 f=Path('results/dev_aux/task2441');done=json.loads((f/'completion.json').read_text());slots=json.loads((f/'slots.json').read_text());games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())};registration=json.loads((f/'registration.json').read_text());baseline=registration['baseline'];rows=[]
 for price in registration['train_grid']:
  selected=[s for s in slots if[s['ratio'],s['hand_ratio']]==price];bounds=[];counts=Counter()
  for s in selected:
   g=games.get(s['slot']);reward=None if g is None else g['reward'];counts['U'if reward is None else g['outcome']]+=1;bounds.append((-1,1)if reward is None else(reward,reward))
  rows.append(dict(price=price,planned=len(selected),counts={x:counts[x]for x in'WLDU'},bounds=[sum(b[i]for b in bounds)/len(bounds)for i in(0,1)]))
 b=next(r for r in rows if r['price']==baseline);eligible=[r for r in rows if r['bounds'][0]>b['bounds'][1]];chosen=min(eligible,key=lambda r:(-r['bounds'][0],r['price']))if eligible else b
 result=dict(status='IMMUTABLE_STRICT_D3_DESIGN_TRAIN_SELECTION',selected=chosen['price'],baseline=baseline,rows=rows,criterion=registration['selection'],actual_games=len(games),unreturned=len(slots)-len(games),completion_status=done['status'],utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),train_games_sha=hashlib.sha256((f/'games.jsonl').read_bytes()).hexdigest(),reserve_queried_before_selection=False,scope='Six finite candidates, not continuousmetric/convergence;4structuralDESIGNfamilyclusters/roles, actualruleW-L. U/missing[-1,1], noquantityreward orignorecensoring. Reserve untouched untilthisimmutablefile. Baseline noimprovementmeans16baselineonlyreserve, nofakecontrast.')
 with(OUT/'selection.json').open('x',encoding='utf-8')as fp:json.dump(result,fp,indent=2)
 print(json.dumps(result))
if __name__=='__main__':select()

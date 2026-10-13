from pathlib import Path
import json,hashlib,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task962';O.mkdir(exist_ok=False);checked=0;paths=0
for task,gamefiles in [(892,[886,890]),(936,[923,929])]:
 e=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes());sources={n:[json.loads(l) for l in (R/f'results/dev_aux/task{n}/games.jsonl').open()] for n in gamefiles};values={}
 for row in e['grid']:
  gs=[sources[int(x['file'].split('/')[0][4:])][x['line']-1] for x in row['sources']];vv=[]
  for g in gs:
   t=g['termination'];v=0 if t['kind'].startswith('cap') or t['winner'] is None else 1 if t['winner']==g['color'] else -1;vv.append(v);assert g['weights'][5]==row['price'] and (g['root']['inventory']==4 if task==892 else g['root']['inventory']==8 and g['weights'][7]==90)
  values[row['price']]=F(sum(vv),len(vv));assert str(values[row['price']])==row['J24'];checked+=1
 grid=[r['price'] for r in e['grid']]
 for path in e['paths']:
  steps=[1,2,4] if path.get('method')=='multiscale' else [1];cur=path['initial'];out=[cur]
  while True:
   ix=grid.index(cur);ns=sorted({j for step in steps for j in [ix-step,ix+step] if 0<=j<len(grid)});best=max(ns,key=lambda j:values[grid[j]])
   if values[grid[best]]<=values[cur]:break
   cur=grid[best];out.append(cur)
  assert out==path['path'] and cur==path['endpoint'];paths+=1
# All two-axis scientific means are independently rederived from their exact saved source references.
e=json.loads((R/'results/dev_aux/task951/endpoints.json').read_bytes());cache={n:[json.loads(l) for l in (R/f'results/dev_aux/task{n}/games.jsonl').open()] for n in [923,929,948]}
for row in e['rows']:
 gs=[cache[int(x['file'].split('/')[0][4:])][x['line']-1] for x in row['sources']];assert len(gs)==24;vv=[]
 for g in gs:
  assert g['weights'][5]==row['B'] and g['weights'][7]==g['weights'][11]==row['G'];t=g['termination'];vv.append(0 if t['kind'].startswith('cap') or t['winner'] is None else 1 if t['winner']==g['color'] else -1)
 assert str(F(sum(vv),24))==row['J24'];checked+=1
best=max(F(r['J24']) for r in e['rows']);ties=[{k:r[k] for k in ['B','G','J24']} for r in e['rows'] if F(r['J24'])==best];assert ties==e['best_plateau'] and e['chosen']==ties[0];r=dict(status='PASS_ALL48_VALID_PRICE_BATCH_MEANS_AND12_LOCAL_OPTIMIZER_PATHS',batch_means=checked,paths=paths,first_tie_verified=True,new_go=0,scope='Independent source-index rederivation validNB4 andNBGstock learning only; primaryterminal/noquantity/nofastmate. AllfourB4sourcefitness interpretations rejectedelsewhere.');(O/'result.json').write_text(json.dumps(r,indent=2));print(r)


from pathlib import Path
import json
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1232';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task1228/plan.json').read_bytes());gs=[json.loads(s) for s in (R/'results/dev_aux/task1230/games.jsonl').read_text().splitlines()];assert len(gs)==2688
rows=[];union={}
for arm in ['J','L']:
 union[arm]={720}
 for w in map(F,['0','1/2','1']):
  scores={};cc={}
  for p in D['prices']:
   v={}
   for opp in ['unit_search','uniform_random']:
    ss=[g for g in gs if g['arm']==arm and g['price']==p and g['opponent']==opp];assert len(ss)==96;v[opp]=F(sum((g['label']=='W')-(g['label']=='L') for g in ss),len(ss))
   scores[p]=w*v['unit_search']+(1-w)*v['uniform_random'];cc[p]={o:str(a) for o,a in v.items()}
  best=min(p for p in scores if scores[p]==max(scores.values()));union[arm].add(best);paths=[]
  for start in [360,4096]:
   p=start;path=[p]
   for _ in range(6):
    i=D['prices'].index(p);neighbors=D['prices'][max(0,i-1):min(len(D['prices']),i+2)];n=min(neighbors,key=lambda q:(-scores[q],q))
    if scores[n]<=scores[p]:break
    p=n;path.append(p)
   paths.append(dict(start=start,end=p,path=path))
  rows.append(dict(arm=arm,search_weight=str(w),global_train_selected=best,all_best=[p for p in scores if scores[p]==scores[best]],finite_scores={p:str(v) for p,v in scores.items()},opponent_scores=cc,strict_neighbors=paths))
d=dict(status='FROZEN_TRAIN_ONLY_PRICES_BEFORE_DEVELOPMENT',rows=rows,dev_union_prices={a:sorted(s) for a,s in union.items()},source=D,scope='Primaryνw1/2, exploratoryw0/1 separate. Global/neighbor allfromcachedtrueW-L, nohuman/quantitylabels ordevrefit.')
(O/'selection.json').write_text(json.dumps(d,indent=2));print(rows);print('DEVUNION',d['dev_union_prices'])

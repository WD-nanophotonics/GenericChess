from pathlib import Path
from fractions import Fraction as F
import json,collections,random
R=Path.cwd();D=json.loads((R/'results/dev_aux/task1296/plan.json').read_bytes())
O=R/'results/dev_aux/task1297';O.mkdir(exist_ok=False);rows=[]
for n in D['sources']:
 p=R/f'results/dev_aux/task{n}/games.jsonl'
 if not p.exists():continue
 ss=json.loads((p.parent/'result.json').read_bytes());assert ss['complete'] and not ss['error']
 gs=[json.loads(v) for v in p.read_text().splitlines()]
 for arm in ['J','L']:
  ps=sorted(set(g['price'] for g in gs if g['arm']==arm));seeds=sorted(set(g['root']['seed'] for g in gs));assert len(seeds)==16
  for wstr in D['weights']:
   w=F(wstr);scores={}
   for price in ps:
    by={}
    for seed in seeds:
     vv={}
     for opp in ['unit_search','uniform_random']:
      xx=[g for g in gs if g['arm']==arm and g['price']==price and g['root']['seed']==seed and g['opponent']==opp];assert len(xx)==6
      vv[opp]=F(sum((g['label']=='W')-(g['label']=='L') for g in xx),6)
     by[seed]=w*vv['unit_search']+(1-w)*vv['uniform_random']
    scores[price]=by
   counts=collections.Counter();allbestcount=collections.Counter();ties=collections.Counter();rng=random.Random(D['seed']);curve={p:sum(v.values())/16 for p,v in scores.items()}
   for _ in range(D['bootstrap']):
    ix=[rng.choice(seeds) for s in seeds];v={p:sum(scores[p][i] for i in ix)/16 for p in ps};mx=max(v.values());best=[p for p in ps if v[p]==mx];counts[min(best)]+=1;ties[len(best)]+=1
    allbestcount.update(best)
   rows.append(dict(source=n,arm=arm,weight=wstr,original_curve={p:str(v) for p,v in curve.items()},original_best=[p for p in ps if curve[p]==max(curve.values())],bootstrap_lowest_tie_selector=dict(counts),bootstrap_allmax_membership=dict(allbestcount),bootstrap_number_ties=dict(ties),bootstrap=D['bootstrap'],scope='TRAIN-resampling descriptive selection instability, not probabilitythatpriceistrue or validationfit'))
result=dict(status='DESCRIPTIVE_TRAIN_ONLY_GRID_IDENTIFIABILITY',rows=rows,new_go=0)
(O/'result.json').write_text(json.dumps(result,indent=2));print([{k:v for k,v in x.items() if k not in ['original_curve','bootstrap_allmax_membership']} for x in rows])

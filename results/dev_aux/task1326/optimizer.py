from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1332';O.mkdir()
gs=[json.loads(v) for v in (R/'results/dev_aux/task1313/games.jsonl').read_text().splitlines()]
assert len(gs)==896
seeds=sorted({g['root']['seed'] for g in gs});ps=sorted({g['price'] for g in gs});rows=[]
def paths(scores):
 out=[]
 for i in range(len(ps)):
  path=[ps[i]];j=i
  while True:
   choices=[k for k in [j-1,j+1] if 0<=k<len(ps) and scores[ps[k]]>scores[ps[j]]]
   if not choices:break
   j=min(choices,key=lambda k:(-scores[ps[k]],ps[k]));path.append(ps[j])
  out.append(dict(start=ps[i],end=ps[j],path=path,global_best=scores[ps[j]]==max(scores.values())))
 return out
for arm in ['J','L']:
 for wstr in ['0','1/2','1']:
  w=F(wstr);fd={p:{} for p in ps}
  for p in ps:
   for s in seeds:
    xx=[g for g in gs if g['arm']==arm and g['price']==p and g['root']['seed']==s];assert len(xx)==4
    fd[p][s]=sum((w if g['opponent']=='unit_search' else 1-w)*F((g['label']=='W')-(g['label']=='L'),2) for g in xx)
  curve={p:sum(v.values())/16 for p,v in fd.items()};count={p:collections.Counter() for p in ps};glob=collections.Counter();rng=random.Random(2026389500)
  values={p:[float(fd[p][s]) for s in seeds] for p in ps}
  for _ in range(5000):
   ids=rng.choices(range(16),k=16);sc={p:sum(values[p][i] for i in ids)/16 for p in ps};best=[p for p in ps if sc[p]==max(sc.values())];glob[min(best)]+=1
   for a in paths(sc):count[a['start']][a['end']]+=1
  rows.append(dict(arm=arm,weight=wstr,curve={p:str(v) for p,v in curve.items()},all_starts=paths(curve),bootstrap_lowest_global=dict(glob),bootstrap_end_by_start={p:dict(v) for p,v in count.items()}))
out=dict(status='CACHED_TRAIN_ONLY_ALL7_INITIAL_PLATEAU_MAP',rows=rows,source='task1313',new_go=0,bootstrap=5000,scope='Only TRAIN trueWL; descriptive resampling not probability of true price; no DEV optimization or human fit.')
(O/'result.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in x.items() if not k.startswith('bootstrap')} for x in rows])

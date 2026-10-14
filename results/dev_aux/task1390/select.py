from pathlib import Path
import json,random,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1395';O.mkdir()
gs=[json.loads(v) for v in (R/'results/dev_aux/task1391/games.jsonl').read_text().splitlines()];assert len(gs)==448;ps=sorted({g['leafB'] for g in gs});seeds=sorted({g['root']['seed'] for g in gs});assert len(seeds)==16;rows=[]
for ws in ['0','1/2','1']:
 w=F(ws);fd={}
 for p in ps:
  fd[p]={s:sum((w if g['opponent']=='unit_search' else 1-w)*F((g['label']=='W')-(g['label']=='L'),2) for g in gs if g['leafB']==p and g['root']['seed']==s) for s in seeds}
 sc={p:sum(x.values())/16 for p,x in fd.items()};best=[p for p in ps if sc[p]==max(sc.values())];paths=[]
 for i in range(7):
  j=i;path=[ps[j]]
  while True:
   nn=[k for k in [j-1,j+1] if 0<=k<7 and sc[ps[k]]>sc[ps[j]]]
   if not nn:break
   j=min(nn,key=lambda k:(-sc[ps[k]],ps[k]));path.append(ps[j])
  paths.append(dict(start=ps[i],end=ps[j],path=path))
 rng=random.Random(2026479500);vals={p:[float(fd[p][s]) for s in seeds] for p in ps};counts=collections.Counter()
 for _ in range(5000):
  ids=rng.choices(range(16),k=16);ss={p:sum(vals[p][i] for i in ids)/16 for p in ps};bb=[p for p in ps if ss[p]==max(ss.values())];counts[min(bb)]+=1
 rows.append(dict(weight=ws,selected=min(best),all_best=best,scores={p:str(x) for p,x in sc.items()},paths=paths,bootstrap_selector=dict(counts)))
dev=sorted({720}|{r['selected'] for r in rows});out=dict(status='FROZEN_TRAIN_ONLY_B_AXIS_BEFORE_DEV',rows=rows,DEV_union=dev,DEV_cases=16*4*len(dev),scope='Primaryw.5 conditionalB axis,R1728/N720native720; no Bhumanfit, sample16uncertain, global lowesttie notnaturaloptimizer convergence; next16DEV untouched.')
(O/'selection.json').write_text(json.dumps(out,indent=2));print(rows);print('DEV',dev)

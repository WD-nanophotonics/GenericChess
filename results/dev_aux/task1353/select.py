from pathlib import Path
import json,random,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1359';O.mkdir()
p=R/'results/dev_aux/task1357';assert json.loads((p/'result.json').read_bytes())['complete']
gs=[json.loads(v) for v in (p/'games.jsonl').read_text().splitlines()];ps=sorted({g['price'] for g in gs});rows=[]
for phase in ['TRAIN_A','TRAIN_B']:
 for wstr in ['0','1/2','1']:
  w=F(wstr);seeds=sorted({g['root']['seed'] for g in gs if g['root']['phase']==phase});assert len(seeds)==32
  fd={price:{} for price in ps}
  for price in ps:
   for seed in seeds:
    xx=[g for g in gs if g['price']==price and g['root']['seed']==seed];assert len(xx)==4
    fd[price][seed]=sum((w if g['opponent']=='unit_search' else 1-w)*F((g['label']=='W')-(g['label']=='L'),2) for g in xx)
  scores={price:sum(vals.values())/32 for price,vals in fd.items()};best=[price for price in ps if scores[price]==max(scores.values())];paths=[]
  for i in range(7):
   j=i;path=[ps[j]]
   while True:
    nexts=[k for k in [j-1,j+1] if 0<=k<7 and scores[ps[k]]>scores[ps[j]]]
    if not nexts:break
    j=min(nexts,key=lambda k:(-scores[ps[k]],ps[k]));path.append(ps[j])
   paths.append(dict(start=ps[i],end=ps[j],path=path))
  rng=random.Random(2026419500);vals={p:[float(fd[p][s]) for s in seeds] for p in ps};counts=collections.Counter();ties=collections.Counter()
  for _ in range(5000):
   ids=rng.choices(range(32),k=32);sc={p:sum(vals[p][i] for i in ids)/32 for p in ps};bb=[p for p in ps if sc[p]==max(sc.values())];counts[min(bb)]+=1;ties[len(bb)]+=1
  rows.append(dict(TRAIN=phase,search_weight=wstr,global_selected=min(best),all_best=best,scores={p:str(v) for p,v in scores.items()},strict_neighbor_all7=paths,bootstrap_selector=dict(counts),bootstrap_ties=dict(ties)))
dev=sorted({720,1440}|{r['global_selected'] for r in rows})
out=dict(status='TRAIN_ONLY_TWO_SAMPLE_SELECTION_BEFORE_DEV',rows=rows,DEV_union=dev,DEV_count=64*4*len(dev),scope='w1/2primary,w0/1exploratory fixed; global lowest-price tie; TRAIN only; identical global result acrossinitials is construction not convergence evidence; all strictneighbor paths retained, humanfit/DEVselection forbidden.')
(O/'selection.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in r.items() if not k.startswith('bootstrap')} for r in rows]);print('DEV_union',dev)

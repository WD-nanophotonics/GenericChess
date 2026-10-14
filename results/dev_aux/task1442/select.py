from pathlib import Path
import json,random,collections,hashlib
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1444';O.mkdir(exist_ok=False)
P=R/'results/dev_aux/task1437';manifest=json.loads((R/'results/dev_aux/task1436/train_manifest.json').read_bytes())
result=json.loads((P/'result.json').read_bytes());assert result['complete'] and result['closed_games']==2048 and result['all_owned_engines_closed']
gs=[json.loads(v) for v in (P/'games.jsonl').read_text().splitlines()]
pairs=sorted({(g['leafR'],g['leafB']) for g in gs});seeds=sorted({g['root']['seed'] for g in gs});assert len(pairs)==16 and len(seeds)==32
rg=sorted({p[0] for p in pairs});bg=sorted({p[1] for p in pairs});rows=[]
for ws in ['0','1/2','1']:
 w=F(ws);fd={}
 for p in pairs:
  fd[p]={s:sum((w if g['opponent']=='unit_search' else 1-w)*F((g['label']=='W')-(g['label']=='L'),2) for g in gs if (g['leafR'],g['leafB'])==p and g['root']['seed']==s) for s in seeds}
 sc={p:sum(x.values())/32 for p,x in fd.items()};best=[p for p in pairs if sc[p]==max(sc.values())];paths=[]
 for p in pairs:
  current=p;path=[p]
  while True:
   i,j=rg.index(current[0]),bg.index(current[1]);neighbours=[]
   for ii,jj in [(i-1,j),(i+1,j),(i,j-1),(i,j+1)]:
    if 0<=ii<len(rg) and 0<=jj<len(bg):
     q=(rg[ii],bg[jj])
     if sc[q]>sc[current]:neighbours.append(q)
   if not neighbours:break
   current=min(neighbours,key=lambda q:(-sc[q],q));path.append(current)
  paths.append(dict(start=p,end=current,path=path))
 vals={p:[float(fd[p][s]) for s in seeds] for p in pairs};rng=random.Random(2026539500);counts=collections.Counter()
 for _ in range(5000):
  ids=rng.choices(range(32),k=32);scores={p:sum(vals[p][i] for i in ids)/32 for p in pairs};mx=max(scores.values());counts[min(p for p in pairs if scores[p]==mx)]+=1
 rows.append(dict(weight=ws,selected=min(best),all_best=best,scores={str(p):str(x) for p,x in sc.items()},paths=paths,bootstrap_selector={str(p):n for p,n in counts.items()}))
primary=next(r['selected'] for r in rows if r['weight']=='1/2')
dev=sorted({(720,720),(1728,720),tuple(primary)})
selection=dict(status='TRAIN_ONLY_COUPLED_GLOBAL_AND_STRICT_NEIGHBORS',primary=primary,rows=rows,DEV_union=dev,scope='16TRAIN,16DEV untouched. Global lowestR thenlowestB is construction, not naturalconvergence. Bootstrap selection descriptive, not probabilitytrueprice. Onlymixedprimary plus fixedtransfercomparisons, no exploratorynu priceunion, no humanfit.')
(O/'selection.json').write_text(json.dumps(selection,indent=2))
d=dict(manifest,root_range=[32,96],root_count=64,expected_games=64*4*len(dev),max_seconds=180,expected_seconds=60,profiles={f'R{r}B{b}':dict(nativeR=720,leafR=r,leafB=b) for r,b in dev},scope='DEV16 frozen TRAINmixedglobal plus old1728/720 and1440/720, dedupbeforeplay; no DEVselection. ActualH48/4096, primary versus720/720.')
(O/'dev_manifest.json').write_text(json.dumps(d,indent=2))
high=dict(d,nodes=4096,max_seconds=400,expected_seconds=180,scope='Frozen64DEV highnodebridge sameTRAINselection, sameprices/RNG/H48, teacherandcandidateboth4096; no pricefit');(O/'dev_high_manifest.json').write_text(json.dumps(high,indent=2))
(O/'selection_inputs.json').write_text(json.dumps(dict(games_sha256=hashlib.sha256((P/'games.jsonl').read_bytes()).hexdigest(),manifest_sha256=hashlib.sha256((R/'results/dev_aux/task1436/train_manifest.json').read_bytes()).hexdigest(),audit='task1443/result.json'),indent=2))
print('PRIMARY',primary,'DEV',dev);print([{k:v for k,v in x.items() if k in ['weight','selected','all_best','scores','bootstrap_selector']} for x in rows])


from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1467';O.mkdir(exist_ok=False);gs=[json.loads(x) for x in (R/'results/dev_aux/task1461/games.jsonl').read_text().splitlines()];assert len(gs)==256
ps=[180,360,720,1440];seeds=sorted({g['root']['seed'] for g in gs});assert len(seeds)==16;rows=[]
for ws in ['0','1/2','1']:
 w=F(ws);fd={p:{s:sum((w if g['opponent']=='unit_search' else 1-w)*F((g['label']=='W')-(g['label']=='L'),2) for g in gs if g['leafP']==p and g['root']['seed']==s) for s in seeds} for p in ps};sc={p:sum(x.values())/16 for p,x in fd.items()};best=[p for p in ps if sc[p]==max(sc.values())];paths=[]
 for i in range(4):
  j=i;path=[ps[j]]
  while True:
   nn=[k for k in [j-1,j+1] if 0<=k<4 and sc[ps[k]]>sc[ps[j]]]
   if not nn:break
   j=min(nn,key=lambda k:(-sc[ps[k]],ps[k]));path.append(ps[j])
  paths.append(dict(start=ps[i],end=ps[j],path=path))
 rng=random.Random(2026559500);counts=collections.Counter()
 for _ in range(5000):
  sample=rng.choices(seeds,k=16);ss={p:sum(fd[p][s] for s in sample)/16 for p in ps};counts[min(p for p in ps if ss[p]==max(ss.values()))]+=1
 rows.append(dict(weight=ws,selected=min(best),all_best=best,scores={p:str(x) for p,x in sc.items()},paths=paths,bootstrap_selector=dict(counts)))
primary=next(x['selected'] for x in rows if x['weight']=='1/2');dev=sorted({720,primary});manifest=json.loads((R/'results/dev_aux/task1460/manifest.json').read_bytes());manifest.update(root_range=[16,32],root_count=16,expected_games=16*4*len(dev),max_seconds=120,expected_seconds=35,profiles={f'P{v}':dict(nativeR=720,leafR=1728,leafN=720,leafB=720,leafP=v) for v in dev},scope='DEV16 frozenbeforeplay, onlyTRAINmixedP versusoldbaselineP720, fixedR1728,N/B720; fullPpromotions/EP, no DEVfit/naturalconvergenceclaim.')
out=dict(status='TRAIN_ONLY_CONDITIONAL_PAWN_AXIS_FROZEN_DEV',primary=primary,rows=rows,DEV_union=dev,scope='16TRAIN fourPgrid, oneprimarymixedgloballowesttie. R1728,N/B720nativePNBR720fixed,Q1664; no humanfit. BothP720sameprice testsdedupnotindependentgain.')
(O/'selection.json').write_text(json.dumps(out,indent=2));(O/'dev_manifest.json').write_text(json.dumps(manifest,indent=2));print(out)

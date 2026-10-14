from pathlib import Path
import json,collections,random,hashlib
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1485';O.mkdir(exist_ok=False)
ps=[180,360,720,1440];out={'status':'BOTH_TRAIN_ONLY_FREEZE_BEFORE_DEV','groups':{},'scope':'H48/1024 actual W-L; C unresolved; paired family units; no human/reference fitting.'}
for group,tid,manifest in [('early',1474,'train_early.json'),('late',1475,'train_late.json')]:
 P=R/f'results/dev_aux/task{tid}';run=json.loads((P/'result.json').read_bytes());assert run['complete'] and run['closed_games']==256 and run['all_owned_engines_closed']
 gs=[json.loads(x) for x in (P/'games.jsonl').read_text().splitlines()];assert len(gs)==256
 seeds=sorted({g['root']['seed'] for g in gs});assert len(seeds)==16;rows=[]
 for ws in ['0','1/2','1']:
  w=F(ws);fd={p:{s:sum((w if g['opponent']=='unit_search' else 1-w)*F((g['label']=='W')-(g['label']=='L'),2) for g in gs if g['leafP']==p and g['root']['seed']==s) for s in seeds} for p in ps};sc={p:sum(x.values())/16 for p,x in fd.items()};best=[p for p in ps if sc[p]==max(sc.values())];paths=[]
  for i in range(4):
   j=i;path=[ps[j]]
   while True:
    nn=[k for k in [j-1,j+1] if 0<=k<4 and sc[ps[k]]>sc[ps[j]]]
    if not nn:break
    j=min(nn,key=lambda k:(-sc[ps[k]],ps[k]));path.append(ps[j])
   paths.append(dict(start=ps[i],end=ps[j],path=path))
  rng=random.Random(2026579500);counts=collections.Counter()
  for _ in range(5000):
   sample=rng.choices(seeds,k=16);ss={p:sum(fd[p][s] for s in sample)/16 for p in ps};counts[min(p for p in ps if ss[p]==max(ss.values()))]+=1
  rows.append(dict(weight=ws,selected=min(best),all_best=best,scores={p:str(x) for p,x in sc.items()},paths=paths,bootstrap_selector=dict(counts),family_scores={p:{s:str(v) for s,v in x.items()} for p,x in fd.items()}))
 out['groups'][group]={'primary':next(x['selected'] for x in rows if x['weight']=='1/2'),'rows':rows,'input_games_sha256':hashlib.sha256((P/'games.jsonl').read_bytes()).hexdigest()}
union=sorted({720,*[x['primary'] for x in out['groups'].values()]});out['DEV_union']=union
for group,lo,hi in [('early',16,48),('late',64,96)]:
 plan=json.loads((R/'results/dev_aux/task1473'/f'train_{group}.json').read_bytes());plan.update(root_range=[lo,hi],root_count=32,expected_games=128*len(union),max_seconds=180,expected_seconds=90,profiles={f'P{v}':dict(nativeR=720,leafR=1728,leafN=720,leafB=720,leafP=v) for v in union},scope='Frozen DEV32 '+group+'; both TRAIN-selected prices and fixed720 dedup; primary own-minus720; secondary own-minus-other. No DEVfit or horizon/grid extension.');(O/f'dev_{group}.json').write_text(json.dumps(plan,indent=2))
(O/'selection.json').write_text(json.dumps(out,indent=2));print({g:{'primary':v['primary'],'scores':[x['scores'] for x in v['rows']],'paths':v['rows'][1]['paths']} for g,v in out['groups'].items()});print('DEV union',union)

from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1384';O.mkdir()
gs=[json.loads(v) for v in (R/'results/dev_aux/task1380/games.jsonl').read_text().splitlines()];key=lambda g:(g['root']['seed'],g['color'],g['opponent'])
by={p:{key(g):g for g in gs if g['price']==p} for p in [720,1440,1728]};seeds=sorted({k[0] for k in by[720]});assert len(seeds)==64
y=lambda g:F((g['label']=='W')-(g['label']=='L'));rows=[]
for p,q,tag in [(1728,720,'PRIMARY_TRAIN_A1728_BASE'),(1440,720,'SECONDARY_OLD1440_BASE'),(1728,1440,'SECONDARY_NEW_MINUS_OLD')]:
 for ws in ['0','1/2','1']:
  w=F(ws);fd={s:sum((w if opp=='unit_search' else 1-w)*sum(y(by[p][s,c,opp])-y(by[q][s,c,opp]) for c in [False,True])/2 for opp in ['unit_search','uniform_random']) for s in seeds};m=sum(fd.values())/64;rng=random.Random(2026459500);v=[float(x) for x in fd.values()];boot=sorted(sum(rng.choices(v,k=64))/64 for _ in range(5000));rows.append(dict(comparison=tag,weight=ws,mean=str(m),bootstrap95=[boot[124],boot[4874]],family_deltas={s:str(x) for s,x in fd.items()}))
counts={p:{opp:dict(collections.Counter(g['label'] for g in gs if g['price']==p and g['opponent']==opp)) for opp in ['unit_search','uniform_random']} for p in by}
out=dict(status='PROSPECTIVE64_H48_FIXED_TRAIN_PRICE_CONFIRMATION',rows=rows,counts=counts,new_go=0,scope='One primary: preselected TRAIN_A mixed1728 vs720; sameTRAIN_B1728 not replicatedDEV; secondary old2and direct difference, nu0/1 exploratory. ActualH48 W-L, C unresolved; noH24failure rewriting or price selection/Humanfit; no universal/infiniteWDL claim.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(counts);print([{k:v for k,v in r.items() if k!='family_deltas'} for r in rows])

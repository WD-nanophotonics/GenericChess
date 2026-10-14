from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1500';O.mkdir(exist_ok=False);study=json.loads((R/'results/dev_aux/task1498/study.json').read_bytes());gs=[json.loads(x) for x in (R/'results/dev_aux/task1499/choices.jsonl').read_text().splitlines()];assert len(gs)==3072;rows=[]
for budget in study['nodes']:
 xx=[x for x in gs if x['node_budget']==budget];ps=study['R_grid'];families=sorted({x['family'] for x in xx});assert len(families)==128
 fd={p:{f:F(sum(x['chosen_WDL'] for x in xx if x['leafR']==p and x['family']==f),2) for f in families} for p in ps};sc={p:sum(v.values())/128 for p,v in fd.items()};best=[p for p in ps if sc[p]==max(sc.values())];paths=[]
 for i in range(4):
  j=i;path=[ps[j]]
  while True:
   nn=[k for k in [j-1,j+1] if 0<=k<4 and sc[ps[k]]>sc[ps[j]]]
   if not nn:break
   j=min(nn,key=lambda k:(-sc[ps[k]],ps[k]));path.append(ps[j])
  paths.append({'start':ps[i],'end':ps[j],'path':path})
 rng=random.Random(2026610500+budget);cnt=collections.Counter()
 for _ in range(5000):
  draw=rng.choices(families,k=128);ss={p:sum(fd[p][f] for f in draw)/128 for p in ps};cnt[min(p for p in ps if ss[p]==max(ss.values()))]+=1
 rows.append({'budget':budget,'selected':min(best),'all_best':best,'scores':{p:str(v) for p,v in sc.items()},'paths':paths,'selector_bootstrap':dict(cnt)})
out={'status':'TRAIN_ONLY_TRUE_GRAPH_WDL_SELECTOR','rows':rows,'DEV_union':sorted({720,*[x['selected'] for x in rows]}),'scope':'3separate fixed-budget selectors; global lowesttie not natural convergence. Exact perfect-play continuation WDL; no human reference fitting, DEV not used.'};(O/'selection.json').write_text(json.dumps(out,indent=2));print(out)

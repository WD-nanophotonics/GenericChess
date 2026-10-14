from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1374';O.mkdir()
old=[json.loads(v) for v in (R/'results/dev_aux/task1361/games.jsonl').read_text().splitlines()];new=[json.loads(v) for v in (R/'results/dev_aux/task1370/games.jsonl').read_text().splitlines()];key=lambda g:(g['price'],g['root']['seed'],g['color'],g['opponent'])
a={key(g):g for g in old};b={key(g):g for g in new};assert set(a)==set(b) and len(a)==768
for k,x in a.items():
 z=b[k];assert x['actions']==z['actions'][:len(x['actions'])]
 if x['label']!='C':assert x['label']==z['label'] and x['termination']==z['termination'] and x['final_fen']==z['final_fen']
labels=lambda g:F((g['label']=='W')-(g['label']=='L'))
seeds=sorted({k[1] for k in a});rows=[]
for p in [1440,1728]:
 for ws in ['0','1/2','1']:
  w=F(ws);fd24={};fd48={}
  for s in seeds:
   for dest,source in [(fd24,a),(fd48,b)]:
    dest[s]=sum((w if opp=='unit_search' else 1-w)*sum(labels(source[p,s,c,opp])-labels(source[720,s,c,opp]) for c in [False,True])/2 for opp in ['unit_search','uniform_random'])
  diff={s:fd48[s]-fd24[s] for s in seeds};rng=random.Random(2026449500)
  stats={}
  for tag,fd in [('H24',fd24),('H48',fd48),('H48_minus_H24',diff)]:
   vv=[float(v) for v in fd.values()];boot=sorted(sum(rng.choices(vv,k=64))/64 for _ in range(5000));stats[tag]=dict(mean=str(sum(fd.values())/64),bootstrap95=[boot[124],boot[4874]])
  rows.append(dict(price=p,weight=ws,stats=stats))
counts={p:{opp:dict(collections.Counter(g['label'] for g in new if g['price']==p and g['opponent']==opp)) for opp in ['unit_search','uniform_random']} for p in [720,1440,1728]}
transitions={p:{opp:dict(collections.Counter(a[k]['label']+'>'+b[k]['label'] for k in a if k[0]==p and k[3]==opp)) for opp in ['unit_search','uniform_random']} for p in [720,1440,1728]}
out=dict(status='PASS768_EXACT_H24_ACTION_PREFIX_AND_PAIRED_H48_OBJECTIVE_RESPONSE',prefix_controls=768,rows=rows,counts_H48=counts,transitions=transitions,new_go=0,scope='Separate declared horizon mechanism on sameDEV, no originalH24rewrite/price refit; direct delta48-delta24 paired not CI-overlap test. Cunresolved notdraw. No infiniteWDL or independentsecondvalidation.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(counts);print(rows)

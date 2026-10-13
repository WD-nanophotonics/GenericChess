
from pathlib import Path
from fractions import Fraction as F
import json,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1209';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task1208/plan.json').read_bytes())
path=R/f"results/dev_aux/task{D['source']}";summary=json.loads((path/'result.json').read_bytes());assert summary['complete'] and not summary['error'];gs=[json.loads(s) for s in (path/'games.jsonl').read_text().splitlines()]
idx={(g['root']['seed'],g['root']['variant'],g['color'],g['opponent']):g for g in gs};assert len(idx)==len(gs)
seeds=sorted(set(g['root']['seed'] for g in gs));y=lambda g:F((g['label']=='W')-(g['label']=='L'));rows=[]
for opp in ['ALL','unit_search','uniform_random']:
 for side in ['ALL','white','black']:
  families={}
  for seed in seeds:
   z=[]
   for color in [False,True]:
    if side!='ALL' and color!=(side=='white'):continue
    beneficiary='white' if color else 'black'
    for o in ['unit_search','uniform_random']:
     if opp!='ALL' and o!=opp:continue
     b=idx[(seed,'none',color,o)];r=idx[(seed,beneficiary+'R',color,o)];n=idx[(seed,beneficiary+'N',color,o)]
     dr=y(r)-y(b);dn=y(n)-y(b);z.append([dr,dn,dr-dn,dr-F(12,5)*dn,dr-dn-F(7,48)])
   families[seed]=[sum(v[j] for v in z)/len(z) for j in range(5)]
  mean=[sum(v[j] for v in families.values())/len(seeds) for j in range(5)];rng=random.Random(D['seed']);boot=[[] for _ in mean]
  for _ in range(D['bootstrap']):
   sample=[families[rng.choice(seeds)] for _ in seeds]
   for j in range(5):boot[j].append(float(sum(v[j] for v in sample)/len(sample)))
  for j in range(5):boot[j].sort()
  ci=[[v[int(.025*(len(v)-1))],v[int(.975*(len(v)-1))]] for v in boot]
  rows.append(dict(opponent=opp,beneficiary=side,families=len(seeds),contrasts=dict(zip(D['contrasts'],map(str,mean))),descriptive_unconditional_bootstrap95=dict(zip(D['contrasts'],ci)),family_contrasts={s:list(map(str,v)) for s,v in families.items()},ratio_point=str(mean[0]/mean[1]) if mean[0]>0 and mean[1]>0 else None,ratio_not_inference=True))
out=dict(status='MATCHED_FINITE_EFFECTS_NO_REFIT',rows=rows,new_go=0,counts=dict(collections.Counter(g['label'] for g in gs)),source=D['source'],scope=D['scope'])
(O/'result.json').write_text(json.dumps(out,indent=2))
for x in rows:
 if x['opponent']=='ALL':print({k:v for k,v in x.items() if k!='family_contrasts'})

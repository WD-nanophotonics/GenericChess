from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1401';O.mkdir()
gs=[json.loads(v) for v in (R/'results/dev_aux/task1397/games.jsonl').read_text().splitlines()];key=lambda g:(g['root']['seed'],g['color'],g['opponent']);base={key(g):g for g in gs if g['leafB']==720};other={key(g):g for g in gs if g['leafB']==360};seeds=sorted({k[0] for k in base});rows=[];y=lambda g:F((g['label']=='W')-(g['label']=='L'))
for ws in ['0','1/2','1']:
 w=F(ws);fd={s:sum((w if opp=='unit_search' else 1-w)*sum(y(other[s,c,opp])-y(base[s,c,opp]) for c in [False,True])/2 for opp in ['unit_search','uniform_random']) for s in seeds};mean=sum(fd.values())/16;rng=random.Random(2026479500);values=[float(x) for x in fd.values()];boot=sorted(sum(rng.choices(values,k=16))/16 for _ in range(5000));rows.append(dict(weight=ws,exploratoryB360_minus_baselineB720=str(mean),bootstrap95=[boot[124],boot[4874]]))
out=dict(status='INDEPENDENT16_B_AXIS_DEV',primary_selected_B=720,primary_gain=0,primary_reason='TRAINmixedselected baseline, zero byconstruction not a second improvement claim',rows=rows,new_go=0,scope='R1728/N720fixed; mainB=Nselected without humanlabel, but sample16 and no evidence unique/generalBprice. Randomtie-selected lowB failspointvalidation; no DEVrefit.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

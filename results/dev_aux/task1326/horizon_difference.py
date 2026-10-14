from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1392';O.mkdir()
gs=[json.loads(v) for v in (R/'results/dev_aux/task1329/games.jsonl').read_text().splitlines()];prefix=json.loads((R/'results/dev_aux/task1349/result.json').read_bytes())['labels'];key=lambda g:(g['root']['seed'],g['color'],g['opponent']);by={p:{key(g):g for g in gs if g['arm']==p} for p in 'BJLO'};seeds=sorted({k[0] for k in by['B']})
y=lambda l:F((l=='W')-(l=='L'));rows=[]
for p in ['J','L','O']:
 fd={s:sum((y(by[p][k]['label'])-y(prefix[by[p][k]['game']]))-(y(by['B'][k]['label'])-y(prefix[by['B'][k]['game']])) for k in by['B'] if k[0]==s)/4 for s in seeds};m=sum(fd.values())/64;rng=random.Random(2026469500);vs=[float(x) for x in fd.values()];boot=sorted(sum(rng.choices(vs,k=64))/64 for _ in range(5000));rows.append(dict(profile=p,paired_delta24_minus_delta12=str(m),bootstrap95=[boot[124],boot[4874]]))
trans={p:dict(collections.Counter(prefix[g['game']]+'>'+g['label'] for g in by[p].values())) for p in 'BJLO'}
(O/'result.json').write_text(json.dumps(dict(status='DIRECT_PAIRED_H24_MINUS_H12_OBJECTIVE_DIFFERENCE',rows=rows,actual_terminal_transitions=trans,new_go=0,scope='Same preserved actualpolicies; nominal CI patterns not comparison test; Cnotdraw, no infiniteWDL or newgames'),indent=2));print(rows);print(trans)

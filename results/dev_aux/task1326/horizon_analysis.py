from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1351';O.mkdir()
gs=[json.loads(v) for v in (R/'results/dev_aux/task1329/games.jsonl').read_text().splitlines()];prefix=json.loads((R/'results/dev_aux/task1349/result.json').read_bytes())['labels']
key=lambda g:(g['root']['seed'],g['color'],g['opponent']);bb={key(g):g for g in gs if g['arm']=='B'};rows=[]
for arm in ['J','L','O']:
 cc={key(g):g for g in gs if g['arm']==arm}
 for h in [12,24]:
  y=lambda g:F(((prefix[g['game']] if h==12 else g['label'])=='W')-((prefix[g['game']] if h==12 else g['label'])=='L'))
  fd={s:sum(y(cc[k])-y(bb[k]) for k in bb if k[0]==s)/4 for s in sorted({k[0] for k in bb})};m=sum(fd.values())/64;rng=random.Random(2026379500);fv=[float(v) for v in fd.values()];boot=sorted(sum(rng.choices(fv,k=64))/64 for _ in range(5000));rows.append(dict(arm=arm,H=h,mixed_gain=str(m),bootstrap95=[boot[124],boot[4874]]))
(O/'result.json').write_text(json.dumps(dict(status='PREFIX_H12_VS_DECLARED_H24',rows=rows,new_go=0,scope='Exposed samepolicy prefix, nominal CIs not adjusted, Cunresolved not draw, no original horizonreset'),indent=2));print(rows)

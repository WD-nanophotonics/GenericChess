from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1452';O.mkdir(exist_ok=False)
gs=[json.loads(v) for v in (R/'results/dev_aux/task1437/games.jsonl').read_text().splitlines()];sel=json.loads((R/'results/dev_aux/task1444/selection.json').read_bytes());roots=json.loads((R/'results/dev_aux/task1432/roots.json').read_bytes())['roots'][:32];seeds=[r['seed'] for r in roots]
assert len(gs)==2048 and set(g['root']['seed'] for g in gs)==set(seeds)
pairs=sorted({(g['leafR'],g['leafB']) for g in gs});rg=sorted({p[0] for p in pairs});bg=sorted({p[1] for p in pairs})
for row in sel['rows']:
 w=F(row['weight']);sc={}
 for p in pairs:
  games=[g for g in gs if (g['leafR'],g['leafB'])==p];assert len(games)==128;v=F(0)
  for opp,weight in [('unit_search',w),('uniform_random',1-w)]:
   sub=[g for g in games if g['opponent']==opp];v+=weight*F(sum((g['label']=='W')-(g['label']=='L') for g in sub),64)
  sc[p]=v;assert F(row['scores'][str(p)])==v
 best=min(p for p in pairs if sc[p]==max(sc.values()));assert tuple(row['selected'])==best
 for path in row['paths']:
  trace=[tuple(p) for p in path['path']];assert trace[0]==tuple(path['start']) and trace[-1]==tuple(path['end'])
  for i,p in enumerate(trace):
   rr,bb=rg.index(p[0]),bg.index(p[1]);nn=[(rg[x],bg[y]) for x,y in [(rr-1,bb),(rr+1,bb),(rr,bb-1),(rr,bb+1)] if 0<=x<4 and 0<=y<4];better=[q for q in nn if sc[q]>sc[p]]
   if i==len(trace)-1:assert not better
   else:assert trace[i+1]==min(better,key=lambda q:(-sc[q],q))
assert sel['primary']==[3407,720]
out=dict(status='PASS_TRAIN32_ONLY_GRID_SCORES_TIES_COORDINATE_PATHS',roots=32,games=2048,primary=sel['primary'],rows=[dict(weight=x['weight'],selected=x['selected'],ends=dict(collections.Counter(str(p['end']) for p in x['paths']))) for x in sel['rows']],new_go=0,scope='Independent64peropponent trueW-L aggregate exactlyreconstructs scores andstrictneighbor choices. Nobootstrapasanoracle; copiedselectiontext16stale explicitlycorrected1451beforeDEV. Baseline/price/nodes frozen.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

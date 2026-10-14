from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1468';O.mkdir(exist_ok=False);gs=[json.loads(x) for x in (R/'results/dev_aux/task1464/games.jsonl').read_text().splitlines()];assert len(gs)==128
key=lambda g:(g['root']['seed'],g['color'],g['opponent']);by={p:{key(g):g for g in gs if g['leafP']==p} for p in [720,1440]};seeds=sorted({k[0] for k in by[720]});assert len(seeds)==16;rows=[];y=lambda g:F((g['label']=='W')-(g['label']=='L'))
for ws in ['0','1/2','1']:
 w=F(ws);fd={s:sum((w if opp=='unit_search' else 1-w)*sum(y(by[1440][s,c,opp])-y(by[720][s,c,opp]) for c in [False,True])/2 for opp in ['unit_search','uniform_random']) for s in seeds};rng=random.Random(2026559501);vals=list(map(float,fd.values()));bs=sorted(sum(rng.choices(vals,k=16))/16 for _ in range(5000));rows.append(dict(weight=ws,mean=str(sum(fd.values())/16),bootstrap95=[bs[124],bs[4874]],family_deltas={s:str(x) for s,x in fd.items()}))
events={}
for p in [720,1440]:
 counts=collections.Counter()
 for g in gs:
  if g['leafP']!=p:continue
  b=__import__('chess').Board(g['root']['fen8'])
  for a in g['actions']:
   m=__import__('chess').Move.from_uci(a['move']);counts['promotions']+=bool(m.promotion);counts['EP']+=b.is_en_passant(m);b.push(m)
 events[p]=dict(counts)
out=dict(status='FROZEN16DEV_CONDITIONAL_PAWN_PRICE',primary='P1440TRAINmixedselected minusbaseline720',rows=rows,counts={p:{opp:dict(collections.Counter(g['label'] for g in gs if g['leafP']==p and g['opponent']==opp)) for opp in ['unit_search','uniform_random']} for p in [720,1440]},actual_promotion_EP_events=events,new_go=0,scope='P/N2 uppergridselected, notordinaryhumanpawnvalue/recoveredfulltable. ConditionalR1728,N/B720,Q1664+contactpawnrankdistribution/nu/H48/nodes1024. Boundarywinner and16familyuncertainty retained, nogridextensionorDEVrefit. WLDactual,Cunresolved.')
(O/'result.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in x.items() if k!='family_deltas'} for x in rows]);print(out['counts'],events)

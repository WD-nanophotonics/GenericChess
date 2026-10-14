from pathlib import Path
import json,collections,random,chess
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1491';O.mkdir(exist_ok=False);sel=json.loads((R/'results/dev_aux/task1485/selection.json').read_bytes());rows={};events={};vectors={}
for group,tid in [('early',1486),('late',1487)]:
 gs=[json.loads(x) for x in (R/f'results/dev_aux/task{tid}/games.jsonl').read_text().splitlines()];assert len(gs)==256
 key=lambda g:(g['root']['seed'],g['color'],g['opponent']);by={p:{key(g):g for g in gs if g['leafP']==p} for p in sel['DEV_union']};seeds=sorted({k[0] for k in by[720]});assert len(seeds)==32
 own=sel['groups'][group]['primary'];other=sel['groups']['late' if group=='early' else 'early']['primary']; rr=[]
 for comparison,p,q in [('primary_own_minus720',own,720),('secondary_own_minus_other',own,other)]:
  for ws in ['0','1/2','1']:
   w=F(ws);y=lambda g:F((g['label']=='W')-(g['label']=='L'));fd={s:sum((w if opp=='unit_search' else 1-w)*sum(y(by[p][s,c,opp])-y(by[q][s,c,opp]) for c in [False,True])/2 for opp in ['unit_search','uniform_random']) for s in seeds};rng=random.Random(2026579501);vals=list(map(float,fd.values()));bs=sorted(sum(rng.choices(vals,k=32))/32 for _ in range(10000));rr.append(dict(comparison=comparison,weight=ws,mean=str(sum(fd.values())/32),bootstrap95=[bs[249],bs[9749]],family_deltas={s:str(x) for s,x in fd.items()}))
   if comparison.startswith('primary') and ws=='1/2':vectors[group]=vals
 counts={p:{opp:dict(collections.Counter(g['label'] for g in gs if g['leafP']==p and g['opponent']==opp)) for opp in ['unit_search','uniform_random']} for p in sel['DEV_union']}
 ev={};trans={opp:dict(collections.Counter(by[720][s,c,opp]['label']+'->'+by[own][s,c,opp]['label'] for s in seeds for c in [False,True])) for opp in ['unit_search','uniform_random']}
 for p in sel['DEV_union']:
  cc=collections.Counter();times=collections.defaultdict(list)
  for g in gs:
   if g['leafP']!=p:continue
   b=chess.Board(g['root']['fen8']);times[g['label']].append(len(g['actions']))
   for a in g['actions']:
    m=chess.Move.from_uci(a['move']);cc['promotions']+=bool(m.promotion);cc['EP']+=b.is_en_passant(m);b.push(m)
  ev[p]={'events':dict(cc),'terminal_plies':dict(times)}
 rows[group]={'rows':rr,'counts':counts,'paired_label_transitions':trans};events[group]=ev
# Two separate independent mu-family samples; common bootstrap draw index per mu, maxT simultaneous bands for exactly two primary means.
means={g:sum(v)/32 for g,v in vectors.items()};rng=random.Random(2026579502);mx=[]
for _ in range(10000):
 draws={g:sum(rng.choices(v,k=32))/32 for g,v in vectors.items()};mx.append(max(abs(draws[g]-means[g]) for g in means))
mx.sort();radius=mx[9499];out={'status':'FROZEN_BOTH32DEV_TRUE_WL','groups':rows,'events':events,'two_primary_simultaneous95_centered_maxT':{g:[m-radius,m+radius] for g,m in means.items()},'scope':'Each mean own TRAIN price minus fixed720 on new32 families. Horizon48 W-L only; C unresolved. Both ownprices360 so crossprice comparison identically0, no independent equivalence/transfer proof. Simultaneous centered bootstrap descriptive, no infinite WDL/human-table recovery.','new_go':0}
(O/'result.json').write_text(json.dumps(out,indent=2));print({g:[{k:v for k,v in z.items() if k!='family_deltas'} for z in x['rows']] for g,x in rows.items()});print(out['two_primary_simultaneous95_centered_maxT']);print({g:x['counts'] for g,x in rows.items()})

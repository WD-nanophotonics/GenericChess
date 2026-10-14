from pathlib import Path
import json,collections,random,hashlib
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1422';O.mkdir(exist_ok=False)
gs=[json.loads(v) for v in (R/'results/dev_aux/task1412/games.jsonl').read_text().splitlines()];assert len(gs)==128
key=lambda g:(g['root']['seed'],g['color'],g['opponent'])
by={p:{key(g):g for g in gs if (g['leafR'],g['leafB'])==p} for p in [(1440,720),(1728,720)]};seeds=sorted({k[0] for k in by[(1728,720)]});assert len(seeds)==16
y=lambda g:F((g['label']=='W')-(g['label']=='L'));rows=[]
for ws in ['0','1/2','1']:
 w=F(ws);fd={s:sum((w if opp=='unit_search' else 1-w)*sum(y(by[(1728,720)][s,c,opp])-y(by[(1440,720)][s,c,opp]) for c in [False,True])/2 for opp in ['unit_search','uniform_random']) for s in seeds}
 vals=[float(v) for v in fd.values()];rng=random.Random(2026499501);bs=sorted(sum(rng.choices(vals,k=16))/16 for _ in range(5000))
 rows.append(dict(comparison='SECONDARY_FIXED1728_MINUS_OLD1440',weight=ws,mean=str(sum(fd.values())/16),bootstrap95=[bs[124],bs[4874]],family_deltas={s:str(v) for s,v in fd.items()}))
paths=json.loads((R/'results/dev_aux/task1408/selection.json').read_bytes());ends={x['weight']:dict(collections.Counter(str(v['end']) for v in x['paths'])) for x in paths['rows']}
counts={str(p):{opp:dict(collections.Counter(g['label'] for g in gs if (g['leafR'],g['leafB'])==p and g['opponent']==opp)) for opp in ['unit_search','uniform_random']} for p in by}
out=dict(status='COUPLED_PAIR_SELECTED_OLD_BASELINE_NO_ADDITIONAL_GAIN',primary_gain='0 by identicalcandidateandbaseline',selected=[1728,720],rows=rows,counts=counts,strict_neighbor_ends=ends,scope='TRAINglobal selectsR1728/B720=N720, sameoldbaseline. Does not estimate universalB=N or newWLgain. All16paths retained, not naturalconvergence. New16DEV128games secondaryfixedtransfer, noDEVbestselection. WLDactual,Cunresolved.')
(O/'result.json').write_text(json.dumps(out,indent=2));print('ends',ends,'counts',counts);print([{k:v for k,v in x.items() if k!='family_deltas'} for x in rows])

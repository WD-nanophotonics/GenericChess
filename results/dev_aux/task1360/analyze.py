from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1363';O.mkdir()
selection=json.loads((R/'results/dev_aux/task1359/selection.json').read_bytes());src=R/'results/dev_aux/task1361';assert json.loads((src/'result.json').read_bytes())['complete']
gs=[json.loads(v) for v in (src/'games.jsonl').read_text().splitlines()];key=lambda g:(g['root']['seed'],g['color'],g['opponent']);base={key(g):g for g in gs if g['price']==720};seeds=sorted({k[0] for k in base});assert len(seeds)==64
y=lambda g:F((g['label']=='W')-(g['label']=='L'));rows=[]
for ss in selection['rows']:
 p=ss['global_selected'];w=F(ss['search_weight']);cand={key(g):g for g in gs if g['price']==p};assert set(cand)==set(base)
 fd={s:sum((w if opp=='unit_search' else 1-w)*sum(y(cand[s,c,opp])-y(base[s,c,opp]) for c in [False,True])/2 for opp in ['unit_search','uniform_random']) for s in seeds}
 m=sum(fd.values())/64;rng=random.Random(2026419500);v=[float(x) for x in fd.values()];boot=sorted(sum(rng.choices(v,k=64))/64 for _ in range(5000))
 rows.append(dict(TRAIN=ss['TRAIN'],weight=ss['search_weight'],TRAIN_selected=p,ratio=str(F(p,720)),mean=str(m),bootstrap95=[boot[124],boot[4874]],family_deltas={s:str(v) for s,v in fd.items()}))
counts={p:{opp:dict(collections.Counter(g['label'] for g in gs if g['price']==p and g['opponent']==opp)) for opp in ['unit_search','uniform_random']} for p in selection['DEV_union']}
out=dict(status='INDEPENDENT64_DEV_TWO_TRAIN_ONLY_PRICE_SELECTION',rows=rows,counts=counts,new_go=0,scope='Each w1/2 PRIMARY selector uses TRAIN only, w0/1 exploratory; A/B sameprice1728 -> SAME DEV test not doubled evidence; point convergence across2samples not uniqueness/multiseed stableproof, nominalclusterboot not adjusted, C unresolved.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(counts);print([{k:v for k,v in r.items() if k!='family_deltas'} for r in rows])

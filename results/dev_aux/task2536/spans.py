"""Exact observed-PV feature spans, not parameter-identifiability proof."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json
T=Path('results/dev_aux/task2534');O=Path('results/dev_aux/task2536')
def insert(basis,values):
 row=list(map(Fraction,values))
 for pivot,base in sorted(basis.items()):
  z=row[pivot]
  if z:row=[a-z*b for a,b in zip(row,base)]
 if not any(row):return False
 pivot=next(i for i,x in enumerate(row)if x);z=row[pivot];basis[pivot]=[x/z for x in row];return True

def run():
 p=json.loads((T/'registration.json').read_text());groups={};counts=Counter()
 for line in(T/'queries.jsonl').open():
  q=json.loads(line)
  if not q['complete']or q['pv_terminal']:continue
  key=q['generator_seed'],q['method'],q['seed'];g=groups.setdefault(key,dict(raw={},active={},witnesses=[],ordinary=0,nonzero_gradient=0));g['ordinary']+=1;phi=q['pv_phi'];insert(g['raw'],phi)
  if any(q['gradient']):
   g['nonzero_gradient']+=1;active=phi[1:]if q['method']=='fixed5'else phi
   if insert(g['active'],active):g['witnesses'].append(dict(game=q['game'],ply=q['ply'],nodes=q['total_nodes'],phi=phi,prediction=q['prediction']))
 rows=[dict(rule=gs,method=method,seed=seed,raw6_feature_rank=len(g['raw']),nonzero_trainable_span_rank=len(g['active']),dimensions=5 if method=='fixed5'else 6,ordinary_PV_queries=g['ordinary'],nonzero_gradient_queries=g['nonzero_gradient'],first_independent_witnesses=g['witnesses'])for(gs,method,seed),g in sorted(groups.items())]
 result=dict(status='PASS_EXACT_OBSERVED_PV_SPANS',models=len(rows),rows=rows,scope='FractionRREF onactualintegerPVfeatures, terminalconstants excluded. Activefixed5 dropsP, free6keepsall; onlynonzeroactualgradientqueries, commonnonzeroscalar preservesfeature-span. Raw6rankreportedseparately. AllTRAIN-exposeddata/no filtering orselection. FullspanisNOTuniqueprice/nonlinearTDidentifiability/terminalcoverage/strength/full-ruleproof; zeroTDerrorsmaystillprovidezerolearningcredit.')
 (O/'spans.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(status=result['status'],models=len(rows),ranks=[(r['rule'],r['method'],r['seed'],r['nonzero_trainable_span_rank'])for r in rows])))
if __name__=='__main__':run()

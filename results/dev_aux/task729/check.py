import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task729'
# Information-per-cost feasibility check, not an unrun fitting claim.
for n in [688,697]:assert json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['status'].startswith('PASS_ALL_')
rows=[]
for task,label in [(687,'A_mean12_24'),(696,'B_q12only')]:
 p=R/f'results/dev_aux/task{task}';r=json.loads((p/'result.json').read_bytes());gs=[json.loads(t) for t in (p/'games.jsonl').open(encoding='utf-8')];b={name:[gs[x['line']-1] for x in rr['batch']['sources']] for rr in r['rows'] for name in rr['names']}
 for start in ['unit','random2514']:
  aa=b[start+'-initial'];bb=b[start+'-endpoint'];rr=[]
  for cap in [12,24]:
   def sign(g):
    q=g['quantity'+str(cap)];return (q>0)-(q<0)
   def result(g):
    if len(g['actions'])<=cap and g['termination']['winner'] is not None:return 1 if g['termination']['winner']==g['color'] else -1
    return sign(g)
   for mode,fn in [('quantity_sign_only',sign),('royal_terminal_first_else_quantity_sign',result)]:
    av=[fn(g) for g in aa];bv=[fn(g) for g in bb];rr.append(dict(cap=cap,mode=mode,initial_wins=sum(v==1 for v in av),endpoint_wins=sum(v==1 for v in bv),initial_losses=sum(v==-1 for v in av),endpoint_losses=sum(v==-1 for v in bv),gain=str(F(sum(bv)-sum(av),32)),distinct_result_cells=sum(x!=y for x,y in zip(av,bv)),all32cells=True))
  rows.append(dict(method=label,start=start,metrics=rr))
out=dict(status='ALL_FROZEN_DEV_CAP_ADJUDICATION_VARIATION_CHECKED',rows=rows,new_go=0,scope='Usercheapmove-capmaterial-countvictory idea: zero-go applysignquantity andterminal-first variants toALREADYfrozen actualA/Bdev. Exploratory post-outcome feasibility only, notnewtrainedmodel/independenttargetholdout. Highwin saturation mayreducesfitnessdiscrimination; no human/referenceprices orcandidateprice selfscoring. No futuregoal/model chosenby favorablemetric; allfourmodels/bothcaps/modes retained.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(rows))

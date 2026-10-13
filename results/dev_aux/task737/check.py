import json,hashlib,collections
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task737';assert json.loads((R/'results/dev_aux/task732/result.json').read_bytes())['status']=='PASS_ALL_ACTUAL_FIXED_UNIT_OPPONENT_PROBES';r=json.loads((R/'results/dev_aux/task731/result.json').read_bytes());gs=[json.loads(t) for t in (R/'results/dev_aux/task731/games.jsonl').open(encoding='utf-8')];rows=[];groups={}
for row in r['rows']:
 games=[gs[x['line']-1] for x in row['batch']['sources']]
 for cap in [12,24]:
  for mode in ['quantity_magnitude','quantity_sign','royal_first_else_quantity_sign']:
   vals=[]
   for g in games:
    q=g['quantity'+str(cap)];v=F(q,19) if mode=='quantity_magnitude' else F((q>0)-(q<0))
    if mode=='royal_first_else_quantity_sign' and len(g['actions'])<=cap and g['termination']['winner'] is not None:v=F(1 if g['termination']['winner']==g['color'] else -1)
    vals.append(v)
   x=dict(pool=row['pool'],names=row['names'],cap=cap,mode=mode,cells=16,goal_mean=str(sum(vals)/16),unique_cell_values=len(set(vals)),value_histogram=dict(collections.Counter(str(z) for z in vals)),goals=[str(z) for z in vals]);rows.append(x);groups.setdefault((row['pool'],cap,mode),[]).append(x)
summary=[dict(pool=p,cap=c,mode=m,unique_price_profiles=len(rr),distinct_all16cell_goal_arrays=len({tuple(x['goals']) for x in rr}),distinct_mean_fitness=len({x['goal_mean'] for x in rr}),all_profiles_saturated_identical_mean=len({x['goal_mean'] for x in rr})==1) for (p,c,m),rr in groups.items()]
out=dict(status='ALL_FIXED_OPPONENT_CHEAP_FEEDBACK_VARIATION_CHECKED',rows=rows,summary=summary,new_go=0,source_sha256=hashlib.sha256((R/'results/dev_aux/task731/games.jsonl').read_bytes()).hexdigest(),scope='Zero-training deriveALL8frozenprofiles/2alreadyexposedrootpools/bothcaps/3feedbackdefinitions fromNEWfixedopponent physicalpilot. Post-outcome feasibility notblindtraining/evolution endpoints, no model/metric cherry-picking. Saturation andfinite distinctness conditionalprice set, notpower/generalWDL/basicvalues proof. Immediatefirstaction for nextwork ispredeclareNEWtrainingroots/candidate budget onlyifnewgoal/opponent premise changesdecision; do notextendoldfits.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(summary))

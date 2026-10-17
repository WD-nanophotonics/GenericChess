"""Actual original TD role-frequency weighting, separate from balanced diagnostic."""
from pathlib import Path
from collections import Counter,defaultdict
from math import sqrt
import json,datetime
D=Path('results/dev_aux/task2545')
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def run():
 actual=defaultdict(Counter)
 for line in Path('results/dev_aux/task2539/games.jsonl').open():
  r=json.loads(line)
  if r['method']=='TD':actual[r['generator_seed'],r['seed']][r['color']]+=1
 cells=json.loads((D/'cells.json').read_text());rows=[];counts=Counter()
 for c in cells:
  if not c['complete_four_family_pair']:continue
  gs,seed,block,t=c['key'];n=actual[gs,seed];den=sum(n.values());a=c['roles'][0]['mean'];b=c['roles'][1]['mean'];d=[(n[0]*x+n[1]*y)/den for x,y in zip(a,b)];z=[dot(a,d),dot(b,d)];rows.append(dict(key=c['key'],role_counts=[n[0],n[1]],role_weights=[n[0]/den,n[1]/den],mixed=d,alignment=z,equal_role_alignment=[c['d0_dot_d'],c['d1_dot_d']],negative=[v<0 for v in z]));counts['complete_cells']+=1;counts['negative_role0']+=z[0]<0;counts['negative_role1']+=z[1]<0;counts['both_positive']+=all(v>0 for v in z);counts['classification_changed_from_equal_roles']+=((z[0]<0)!=c['negative_mixed_role0']or(z[1]<0)!=c['negative_mixed_role1'])
 out=dict(status='ACTUAL_ORIGINAL_TD_GAME_ROLE_FREQUENCY_WEIGHTING',counts=dict(counts),roles=[dict(rule=gs,seed=seed,counts=[v[0],v[1]],weights=[v[0]/sum(v.values()),v[1]/sum(v.values())])for(gs,seed),v in sorted(actual.items())],rows=rows,scope='Same-rule/initial92actualTDgamecounts INCLUDEzero-observation/UNKNOWN. Applytheseweights to existingfrozenWDLtrajectoryrolegroupmeans, notTDtheta/visitationdistribution; this is counterfactual local proxyfit only, not actualdeployedTDgradient. Cells reuse theta acrossblocks/currentproposal, not independentpopulationunits. Original equal-role diagnosticunchanged; no query/update/selection.')
 (D/'training-role-weights.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],counts=dict(counts))))
if __name__=='__main__':run()

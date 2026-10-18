"""Every-query rate/step/loss measurements; not stationary test loss or WLD credit."""
from pathlib import Path
from collections import defaultdict,Counter
from math import sqrt,tanh,isfinite
import json,hashlib
D=Path('results/dev_aux/task2558');A=Path('results/dev_aux/task2560')
def run():
 arms=defaultdict(lambda:dict(count=Counter(),bins=defaultdict(Counter),eta=[],step=[],before=[],after=[]))
 for line in(D/'queries.jsonl').open():
  q=json.loads(line);k=q['generator_seed'],q['method'],q['seed'];a=arms[k];c=a['count'];c['paid_nodes']+=q['nodes'];c['queries']+=1;c['failed']+=not q['complete']
  if not q['observed']:continue
  c['observations']+=1;st=q['learning'];clock=q['clock'];eta=clock['eta'];v=[y-x for x,y in zip(q['weights'],q['weights_after'])];norm=sqrt(sum(x*x for x in v));a['eta'].append(eta);a['step'].append(norm);c['clock_nodes']+=clock['interval_nodes'];c['samples']+=st['samples'];c['active']+=st['active'];c['query_updates']+=st['changed'];c['loss_sum']+=st['loss']*st['samples'];c['eta_sum']+=eta;c['step_length']+=norm;c['terminal_PV']+=q['pv_terminal'];c['zero_step']+=norm==0
  b=a['bins'][min(3,(q['total_nodes']-1)//50000)];b['samples']+=st['samples'];b['loss_sum']+=st['loss']*st['samples'];b['observations']+=1;b['eta_sum']+=eta;b['step_length']+=norm
  if not a['before']:a['before']=q['weights']
  a['after']=q['weights_after']
 rows=[]
 for k,a in sorted(arms.items()):
  c=dict(a['count']);c['tail_uncredited_nodes']=c['paid_nodes']-c['clock_nodes'];assert c['tail_uncredited_nodes']>=0
  if k[1]=='CostClock':assert abs(c['eta_sum']-.05*c['clock_nodes']*27795/3200000)<1e-8
  else:assert abs(c['eta_sum']-.05*c['observations'])<1e-8
  row=dict(rule=k[0],method=k[1],seed=k[2],counts=c,eta_min=min(a['eta'],default=None),eta_max=max(a['eta'],default=None),step_max=max(a['step'],default=None),initial=a['before'],endpoint=a['after'],bins=[dict(bin=i,**dict(b),mean_loss=b['loss_sum']/max(1,b['samples']))for i,b in sorted(a['bins'].items())]);rows.append(row)
 by={}
 for m in ['Mean','CostClock']:
  c=Counter()
  for a in rows:
   if a['method']==m:c.update(a['counts'])
  by[m]=dict(c)
 out=dict(status='PASS_ALL_CLOCK_MASS_IDENTITIES',rows=rows,by_method=by,scope='Loss is one-sided own evolving search-target loss; methods see different samples/policies/targets and rates. Eta mass telescopes to charged completed-observation intervals, includes foe/failed work; trailing nodes are paid but not retrospectively credited. No WLD gradient, normalized deployment, eta clipping or stationary error inference.')
 (A/'signals.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],arms=len(rows),by_method=by)))
if __name__=='__main__':run()

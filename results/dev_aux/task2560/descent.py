"""All-query frozen-target descent diagnostics; no policy/model/eta selection."""
from pathlib import Path
from collections import Counter,defaultdict
from math import tanh,isclose,sqrt,isfinite
import json
D=Path('results/dev_aux/task2558');A=Path('results/dev_aux/task2560')
def objective(w,samples):
 loss=0.
 for s in samples:
  v=tanh(sum(x*y for x,y in zip(w,s['phi']))/10);lo=tanh(float(s['lower'])/10);hi=tanh(float(s['upper'])/10);e=lo-v if v<lo else hi-v if v>hi else 0.;loss+=e*e/2
 return loss/max(1,len(samples))
def run(prefix_rule=None):
 by=defaultdict(Counter);worst={};pairs={}
 for line in(D/'queries.jsonl').open():
  q=json.loads(line)
  if prefix_rule is not None and q['generator_seed']>prefix_rule:break
  if prefix_rule is not None and q['generator_seed']!=prefix_rule:continue
  if not q['observed']:continue
  key=q['generator_seed'],q['method'],q['seed'];c=by[key];before=objective(q['weights'],q['samples']);after=objective(q['weights_after'],q['samples']);assert isclose(before,q['learning']['loss'],abs_tol=1e-12,rel_tol=1e-10)
  step=[a-b for a,b in zip(q['weights_after'],q['weights'])];norm2=sum(x*x for x in step);predicted=norm2/q['clock']['eta'];change=after-before;assert all(map(isfinite,[before,after,predicted]))
  c['observations']+=1;c['before_loss_sum_of_means']+=before;c['after_loss_sum_of_means']+=after;c['linearized_descent_sum']+=predicted;c['increased_beyond_1e12']+=change>1e-12;c['decreased_beyond_1e12']+=change< -1e-12;c['near_unchanged']+=abs(change)<=1e-12;c['nonzero_steps']+=norm2>0
  if key not in worst or change>worst[key]['increase']:worst[key]=dict(increase=change,gameid=q['gameid'],ply=q['ply'],before=before,after=after,eta=q['clock']['eta'],predicted_first_order_descent=predicted,step_norm=sqrt(norm2))
  pairkey=q['generator_seed'],q['seed'];pairs.setdefault(pairkey,{}).setdefault(q['method'],dict(weights=q['weights'],samples=q['samples'],nodes=q['total_nodes'],after=q['weights_after'],eta=q['clock']['eta']))
 # First candidatequery per paired arm has identical actual state/weights/order.
 witnesses=[]
 for key,v in sorted(pairs.items()):
  if set(v)!= {'Mean','CostClock'}:continue
  a,b=v['Mean'],v['CostClock'];assert a['weights']==b['weights']and a['samples']==b['samples']and a['nodes']==b['nodes']
  da=[y-x for x,y in zip(a['weights'],a['after'])];db=[y-x for x,y in zip(b['weights'],b['after'])];factor=b['eta']/a['eta'];assert all(isclose(y,factor*x,rel_tol=1e-9,abs_tol=1e-13)for x,y in zip(da,db));witnesses.append(dict(rule=key[0],seed=key[1],eta_ratio=factor,same_frozen_batch=True,parallel_delta=True))
 rows=[dict(rule=k[0],method=k[1],seed=k[2],counts=dict(c),max_increase=worst[k])for k,c in sorted(by.items())];total={}
 for m in ['Mean','CostClock']:
  c=Counter()
  for k,v in by.items():
   if k[1]==m:c.update(v)
  total[m]=dict(c)
 out=dict(status='PASS_ALL_FROZEN_TARGET_LOSS_AND_FIRST_BATCH_DIRECTION_CHECKS',prefix_rule=prefix_rule,rows=rows,by_method=total,first_paired_batches=witnesses,scope='Local surrogate freezes each actual prequery search bound while recomputing loss after actual update; targets are detached, not recomputed searches. Own evolving data/targets, not stationary validation loss/causal frequency proof/rollout strength. Diagnostic designed during TRAIN before any EVAL; no params/results changed or selected. ALLnegative and maximum-increase examples retained.')
 (A/('descent.json'if prefix_rule is None else'descent-first-rule.json')).write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],by_method=total,first_pairs=len(witnesses))))
if __name__=='__main__':run()

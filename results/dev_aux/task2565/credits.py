"""Raw temporal recommendation cancellation on ACTUAL frozen-policy trajectories.

Shadow statistics only: no counterfactual policy/weight/fitness and no TC training.
"""
from pathlib import Path
from collections import defaultdict,Counter
from math import tanh,isclose
import json,sys,time

def run(directory):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());stream=(json.loads(l)for l in(d/'queries.jsonl').open());q=next(stream,None);net={};absolute={};counts=defaultdict(Counter);roles={};points=[];began=time.perf_counter()
 for g in map(json.loads,(d/'games.jsonl').open()):
  k=str((g['generator_seed'],g['seed'],g['method']));w=g['initial_weights'];preds=[];grads=[];terminals=[]
  if k not in net:net[k]=[0.]*len(w);absolute[k]=[0.]*len(w);roles[k]=[[0.]*len(w),[0.]*len(w)]
  while q is not None and q['gameid']==g['gameid']:
   if q['observed']:
    v=tanh(q['value']/10);grad=[0.]*len(w)if q['pv_terminal']else[x*(1-tanh(sum(a*b for a,b in zip(w,q['pv_phi']))/10)**2)/10 for x in q['pv_phi']]
    if p['domain']=='chess':grad[0]=0.
    preds.append(v);grads.append(grad);terminals.append(q['pv_terminal']);counts[k]['terminal_PV']+=q['pv_terminal']
   q=next(stream,None)
  elig=[0.]*len(w);en=[0.]*len(w);ea=[0.]*len(w)
  for i,(pred,grad)in enumerate(zip(preds,grads)):
   target=preds[i+1]if i+1<len(preds)else g['outcome']
   if target is None:break
   error=target-pred;elig=[p['lambda']*e+x for e,x in zip(elig,grad)];rr=[error*x for x in elig]
   counts[k]['terms']+=1;counts[k]['zero_errors']+=error==0;counts[k]['terminal_forecast_transition']+=i+1<len(preds)and terminals[i+1]and not terminals[i]
   for j,x in enumerate(rr):en[j]+=x;ea[j]+=abs(x)
  assert all(isclose(a+p['eta']*b,c,rel_tol=1e-10,abs_tol=1e-11)for a,b,c in zip(w,en,g['weights']))
  for j in range(len(w)):net[k][j]+=en[j];absolute[k][j]+=ea[j];roles[k][g['color']][j]+=en[j]
  counts[k]['games']+=1;counts[k]['actual_terminal']+=g['outcome']is not None;counts[k]['terminal_white_win']+=g['outcome']==1;counts[k]['terminal_black_win']+=g['outcome']==-1;counts[k]['actual_draw']+=g['outcome']==0
  points.append(dict(key=k,index=g['index'],nodes=g['total_nodes'],shadow_rates=[abs(a)/b if b else 1. for a,b in zip(net[k],absolute[k])]))
 assert q is None
 out=dict(status='ALL_ACTUAL_IMPULSES_RECOUNTED',rows=[dict(key=k,net=net[k],absolute=absolute[k],shadow_rates=[abs(a)/b if b else 1. for a,b in zip(net[k],absolute[k])],role_nets_varying_theta=roles[k],counts=dict(counts[k]))for k in net],seconds=time.perf_counter()-began,scope='Unscaled perTD-error recommendation cancellation on actual96 policies/weights. A is sum of each impulseabsolute, not abs(episode net). Not TC-trained policies, not counterfactual strength, not evidence of pure noise/convergence or fixedtheta roleconflict. No parameter/data/fitness change.')
 (d/'credit-cancellation.json').write_text(json.dumps(out,indent=2));(d/'shadow-rate-curve.json').write_text(json.dumps(points));print(json.dumps(dict(status=out['status'],arms=len(net),terms=sum(c['terms']for c in counts.values()),seconds=out['seconds'])))
if __name__=='__main__':run(sys.argv[1])

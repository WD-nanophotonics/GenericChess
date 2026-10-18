"""TRAIN-only Jacobian/update-direction geometry; no fitted preconditioner."""
from pathlib import Path
import json
import numpy as np
D=Path('results/dev_aux/task2558');A=Path('results/dev_aux/task2560')
def run(prefix_rule=None):
 by={}
 for line in(D/'queries.jsonl').open():
  q=json.loads(line)
  if prefix_rule is not None and q['generator_seed']>prefix_rule:break
  if prefix_rule is not None and q['generator_seed']!=prefix_rule:continue
  if not q['observed']:continue
  k=q['generator_seed'],q['method'],q['seed'];a=by.setdefault(k,dict(jac=np.zeros((6,6)),direction=np.zeros((6,6)),observations=0,active_samples=0,zero_mean_directions=0,cancellation_sum=0.,nonzero_batches=0))
  samples=q['samples'];phi=np.array([s['phi']for s in samples],dtype=float);w=np.array(q['weights']);pred=np.tanh(phi@w/10);lo=np.tanh(np.array([float(s['lower'])for s in samples])/10);hi=np.tanh(np.array([float(s['upper'])for s in samples])/10);err=np.where(pred<lo,lo-pred,np.where(pred>hi,hi-pred,0.));g=phi*((1-pred*pred)/10)[:,None];active=err!=0;ga=g[active];a['jac']+=ga.T@ga;a['active_samples']+=int(active.sum());v=g*err[:,None];m=v.mean(axis=0);a['direction']+=np.outer(m,m);a['observations']+=1;a['zero_mean_directions']+=bool(np.linalg.norm(m)==0)
  expected=np.array(q['weights'])+q['clock']['eta']*m;assert np.allclose(expected,q['weights_after'],rtol=1e-10,atol=1e-12)
  denom=np.linalg.norm(v,axis=1).mean()
  if denom>0:a['cancellation_sum']+=float(np.linalg.norm(m)/denom);a['nonzero_batches']+=1
 def spectrum(M):
  e=np.linalg.eigvalsh(M);assert e[0]>= -1e-12*max(1.,e[-1]);tol=max(1e-16,1e-12*e[-1]);return dict(eigenvalues=e.tolist(),relative_threshold=1e-12,absolute_floor=1e-16,numerical_rank=int(sum(e>tol)),condition_positive=float(e[-1]/e[0])if e[0]>tol else None)
 rows=[]
 for k,a in sorted(by.items()):
  rows.append(dict(rule=k[0],method=k[1],seed=k[2],observations=a['observations'],active_samples=a['active_samples'],zero_mean_directions=a['zero_mean_directions'],mean_cancellation_ratio=a['cancellation_sum']/max(1,a['nonzero_batches']),active_prediction_jacobian=spectrum(a['jac']/max(1,a['active_samples'])),mean_update_direction=spectrum(a['direction']/max(1,a['observations']))))
 out=dict(status='PASS_INDEPENDENT_NUMPY_UPDATE_DIRECTION_RECONSTRUCTION',prefix_rule=prefix_rule,rows=rows,numpy_version=np.__version__,scope='TRAIN-only tanh Jacobians on active one-sided nodes and per-query unscaled mean residual-gradient second moments. Thresholded numerical rank/condition are descriptive along changing policies/targets, not Hessian/Fisher/uniqueoptimum/convergence/strength/critic-context proof. No preconditioner/price normalization/rate/seed selection or new fitness.')
 (A/('conditioning.json'if prefix_rule is None else'conditioning-first-rule.json')).write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],arms=len(rows))))
if __name__=='__main__':run()

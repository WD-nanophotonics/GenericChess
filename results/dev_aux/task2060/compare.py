"""Frozen small sparse-linear projection diagnostic on exact canonical teacher."""
from pathlib import Path
from collections import Counter,defaultdict
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
import json,hashlib,time
import numpy as np
from scripts.generic_proof_rnb_bridge import orbit
ROOT=Path('results/dev_aux/task2060')
def features(raw):
 board=raw[:-1];turn=raw[-1];extras=[(i,p) for i,p in enumerate(board) if p not in ('.','K','k')];owner=int(extras[0][1].islower()) if extras else 0
 own=board.index('k' if owner else 'K');enemy=board.index('K' if owner else 'k');relturn=int(turn==owner);sign=1 if relturn else -1
 ids=[0,1,2+relturn*256+own*16+enemy];vals=[sign*sum(p.upper()=='N' for i,p in extras),sign*sum(p.upper()=='B' for i,p in extras),1.]
 for i,p in extras:
  dx=i%4-own%4+3;dy=i//4-own//4+3;tid=0 if p.upper()=='N' else 1
  ids.append(514+relturn*98+tid*49+dy*7+dx);vals.append(1.)
 while len(ids)<5:ids.append(0);vals.append(0.)
 return ids,vals

def run():
 t=time.perf_counter();p=json.loads((ROOT/'plan.json').read_text());assert json.loads(Path(p['audit']).read_text())['status']=='PASS_COMPLETE_COVERAGE_BELLMAN_RANK_CANONICAL_HISTORY'
 raw=Path(p['teacher']).read_bytes();assert hashlib.sha256(raw).hexdigest()==p['teacher_sha'];labels=[json.loads(x) for x in raw.splitlines()];n=len(labels)
 ids=[];vals=[];ys=[];train=[];family=[]
 for l in labels:
  raw=tuple(l['board']);ix,vs=features(raw);ids.append(ix);vals.append(vs);ys.append({'WIN':1.,'DRAW':0.,'LOSS':-1.}[l['label']])
  canonical=min(orbit(raw));fam=hashlib.sha256(('2060:'+repr(canonical)).encode()).hexdigest();family.append(fam);train.append(int(fam,16)%4!=0)
 ids=np.array(ids,dtype=np.int32);vals=np.array(vals,dtype=np.float64);y=np.array(ys);eligible=np.array([l['status']=='ongoing' for l in labels]);train=np.array(train)&eligible;dev=~np.array([int(f,16)%4!=0 for f in family])&eligible
 assert not set(np.array(family)[train])&set(np.array(family)[dev]);assert int(train.sum()+dev.sum())==int(eligible.sum())
 a=ids[train];v=vals[train];target=y[train];G=np.zeros((710,710));rhs=np.zeros(710)
 for i in range(5):
  np.add.at(rhs,a[:,i],v[:,i]*target)
  for j in range(5):np.add.at(G,(a[:,i],a[:,j]),v[:,i]*v[:,j])
 results={};predictions={};models={}
 for name,size in (('material',2),('kingking',514),('kingpiece',710)):
  weights=np.linalg.solve(G[:size,:size]+p['ridge']*np.eye(size),rhs[:size]);w=np.zeros(710);w[:size]=weights;pred=(w[ids]*vals).sum(axis=1);predictions[name]=pred;models[name]=w.tolist()
  result=dict(features=size,TRAIN_MSE=float(np.mean((pred[train]-y[train])**2)),DEV_MSE=float(np.mean((pred[dev]-y[dev])**2)),DEV_discrete_accuracy=float(np.mean(np.where(pred[dev]>.5,1,np.where(pred[dev]<-.5,-1,0))==y[dev])),DEV_mean_absolute_error=float(np.mean(abs(pred[dev]-y[dev]))))
  byinv={}
  for inv in ('KK','KKN','KKB','KKBN'):
   mask=dev&np.array([l['inventory']==inv for l in labels]);byinv[inv]=dict(n=int(mask.sum()),MSE=float(np.mean((pred[mask]-y[mask])**2)))
  result['by_inventory']=byinv;results[name]=result
 indices=np.flatnonzero(dev);ranking={};nonflat=[]
 for i in indices:
  qs=np.array([-e['child_value'] for e in labels[i]['actions']]);
  if int(qs.max())!=int(qs.min()):nonflat.append(i)
 for name,pred in predictions.items():
  optimistic=[];pessimistic=[];average=[];alloptimal=[];tiecount=[]
  for i in nonflat:
   edges=labels[i]['actions'];q=np.array([-e['child_value'] for e in edges]);scores=np.array([-pred[e['child']] for e in edges]);best=np.flatnonzero(scores>=scores.max()-1e-9);regret=q.max()-q[best]
   optimistic.append(float(regret.min()));pessimistic.append(float(regret.max()));average.append(float(regret.mean()));alloptimal.append(bool(np.all(regret==0)));tiecount.append(len(best))
  ranking[name]=dict(DEV_nonflat_roots=len(nonflat),optimistic_regret=float(np.mean(optimistic)),pessimistic_regret=float(np.mean(pessimistic)),tie_average_regret=float(np.mean(average)),all_top_actions_optimal_fraction=float(np.mean(alloptimal)),mean_top_tie_count=float(np.mean(tiecount)))
 result=dict(status='COMPLETE_FROZEN_REPRESENTATION_DIAGNOSTIC',TRAIN=int(train.sum()),DEV=int(dev.sum()),TRAIN_families=len(set(np.array(family)[train])),DEV_families=len(set(np.array(family)[dev])),no_orbit_overlap=True,DEV_WDL=dict(Counter(labels[i]['label'] for i in indices)),models=results,one_step_action_diagnostic=ranking,seconds=time.perf_counter()-t,scope=p['distribution']+' '+p['split']+' '+p['action'],no_actual_game_strength_claim=True)
 assert result['seconds']<p['seconds_cap'];(ROOT/'models.json').write_text(json.dumps(models,separators=(',',':')));(ROOT/'result.json').write_text(json.dumps(result,indent=2))
 with (ROOT/'split.jsonl').open('x')as f:
  for i in np.flatnonzero(eligible):f.write(json.dumps(dict(index=int(i),family=family[i],phase='TRAIN' if train[i] else 'DEV'))+'\n')
 print(json.dumps(result))
if __name__=='__main__':run()

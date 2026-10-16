"""Frozen nearby-rule sparse-linear transfer, scratch and forgetting curves."""
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
from collections import Counter
import json,hashlib,time,random
import numpy as np
from scripts.generic_proof_rnb_bridge import orbit
from results.dev_aux.task2060.compare import features
OUT=Path('results/dev_aux/task2067')
def load(path):return [json.loads(x)for x in Path(path).read_text().splitlines()]
def key(l):return ''.join(l['board'][:-1])+str(l['board'][-1])
def arrays(labels):
 ids=[];vals=[];ys=[];train=[];eligible=[]
 for l in labels:
  raw=tuple(l['board']);a,v=features(raw);ids.append(a);vals.append(v);ys.append({'WIN':1,'DRAW':0,'LOSS':-1}[l['label']]);f=hashlib.sha256(('2060:'+repr(min(orbit(raw)))).encode()).hexdigest();train.append(int(f,16)%4!=0);eligible.append(l['status']=='ongoing')
 return np.array(ids),np.array(vals),np.array(ys),np.array(train)&np.array(eligible),~np.array(train)&np.array(eligible)
def metrics(w,ids,vals,y,mask):
 pred=(w[ids]*vals).sum(axis=1);return dict(MSE=float(np.mean((pred[mask]-y[mask])**2)),MAE=float(np.mean(abs(pred[mask]-y[mask]))),accuracy=float(np.mean(np.where(pred[mask]>.5,1,np.where(pred[mask]<-.5,-1,0))==y[mask])))
def run():
 t=time.perf_counter();p=json.loads((OUT/'plan.json').read_text());assert json.loads(Path(p['audit']).read_text())['status']=='PASS_COMPLETE_COVERAGE_BELLMAN_RANK_CANONICAL_HISTORY'
 for k in('oldteacher','newteacher','oldmodels'):assert hashlib.sha256(Path(p[k]).read_bytes()).hexdigest()==p[k+'_sha']
 old=load(p['oldteacher']);new=load(p['newteacher']);oi,ov,oy,ot,od=arrays(old);ni,nv,ny,nt,nd=arrays(new);models=json.loads(Path(p['oldmodels']).read_text());population={key(l):l for l in old};counts=Counter();witnesses={}
 for l in new:
  if key(l)not in population:continue
  a=population[key(l)];counts[(a['label'],l['label'])]+=1
  if a['label']!=l['label']:witnesses.setdefault(a['label']+'->'+l['label'],dict(board=l['board'],old_rank=a['rank'],new_rank=l['rank'],old_status=a['status'],new_status=l['status']))
 order=sorted(np.flatnonzero(nt),key=lambda i:hashlib.sha256(('2067sample:'+key(new[i])).encode()).hexdigest());results=[];saved={}
 for name,size in(('material',2),('kingking',514),('kingpiece',710)):
  prior=np.array(models[name]);zero=metrics(prior,ni,nv,ny,nd);oldbase=metrics(prior,oi,ov,oy,od)
  results.append(dict(model=name,method='ZERO_SHOT',samples=0,updates=0,seconds=0,newDEV=zero,oldDEV=oldbase))
  for budget in p['samples']:
   sample=np.array(order[:budget]);assert len(sample)==budget;orders=[];rng=random.Random(p['seed']+budget)
   for epoch in range(p['epochs']):tmp=list(sample);rng.shuffle(tmp);orders+=tmp
   for method in('TRANSFER','SCRATCH'):
    w=prior.copy()if method=='TRANSFER'else np.zeros(710);beg=time.perf_counter()
    for i in orders:
     a=ni[i];v=nv[i];mask=a<size;a=a[mask];v=v[mask];error=float(np.dot(w[a],v)-ny[i]);w[:size]*=1-p['learning_rate']*p['ridge'];np.add.at(w,a,-p['learning_rate']*error*v)
    elapsed=time.perf_counter()-beg;newmet=metrics(w,ni,nv,ny,nd);oldmet=metrics(w,oi,ov,oy,od)
    results.append(dict(model=name,method=method,samples=budget,updates=len(orders),seconds=elapsed,newDEV=newmet,oldDEV=oldmet,new_target_met=newmet['MSE']<=p['target_MSE'],oldDEV_MSE_change=oldmet['MSE']-oldbase['MSE']));saved[f'{name}/{method}/{budget}']=w.tolist()
 crossings={}
 for name in models:
  for method in('TRANSFER','SCRATCH'):
   hits=[r for r in results if r['model']==name and r['method']==method and r['newDEV']['MSE']<=p['target_MSE']];crossings[name+'/'+method]=None if not hits else min(hits,key=lambda r:r['samples'])['samples']
 priorcost=sum(json.loads(Path(x).read_text())['seconds']for x in('results/dev_aux/task2056/result.json','results/dev_aux/task2058/result.json','results/dev_aux/task2059/result.json','results/dev_aux/task2060/result.json'));newcost=sum(json.loads(Path(x).read_text())['seconds']for x in('results/dev_aux/task2064/result.json','results/dev_aux/task2065/result.json','results/dev_aux/task2066/result.json'))
 result=dict(status='COMPLETE_NO_REFIT_OR_MODEL_SELECTION',newTRAIN=int(nt.sum()),newDEV=int(nd.sum()),oldDEV=int(od.sum()),common_state_label_changes={a+'->'+b:n for(a,b),n in counts.items()},first_label_change_witnesses=witnesses,curves=results,first_frozen_target_sample_budget=crossings,prior_teacher_audit_fit_seconds=priorcost,new_teacher_audit_seconds=newcost,total_diagnostic_seconds=time.perf_counter()-t,scope=p['methods']+' '+p['resources'],actualgame_strength_unmeasured=True)
 assert result['total_diagnostic_seconds']<p['seconds_cap'];(OUT/'result.json').write_text(json.dumps(result,indent=2));(OUT/'weights.json').write_text(json.dumps(saved,separators=(',',':')))
 print(json.dumps({k:v for k,v in result.items()if k not in('curves','first_label_change_witnesses')}));print(json.dumps([r for r in results if r['model']=='kingpiece']))
if __name__=='__main__':run()

"""Mechanically generated count-pair basis, scoped exactteacher diagnostic."""
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
import json,time,itertools,hashlib
import numpy as np
from results.dev_aux.task2060.compare import features
from scripts.generic_proof_rnb_bridge import orbit
OUT=Path('results/dev_aux/task2082')
def augmented(raw):
 ids,vals=features(raw);types=('R','N','B')
 for k,(a,b)in enumerate(itertools.combinations_with_replacement(types,2)):
  value=0
  for owner in(0,1):
   na=sum(p== (a.lower()if owner else a)for p in raw[:-1]);nb=sum(p== (b.lower()if owner else b)for p in raw[:-1]);n=na*(na-1)/2 if a==b else na*nb;value+=(1 if owner==raw[-1]else -1)*n
  ids.append(710+k);vals.append(value)
 return ids,vals

def run():
 t=time.perf_counter();p=json.loads((OUT/'plan.json').read_text());assert json.loads(Path(p['audit']).read_text())['status']=='PASS_COMPLETE_COVERAGE_BELLMAN_RANK_CANONICAL_HISTORY';labels=[json.loads(x)for x in Path(p['teacher']).read_text().splitlines()if json.loads(x)['status']=='ongoing'];ids=[];vals=[];target=[];train=[]
 for l in labels:
  raw=tuple(l['board']);a,v=augmented(raw);ids.append(a);vals.append(v);target.append({'WIN':1,'DRAW':0,'LOSS':-1}[l['label']]);f=hashlib.sha256(('2060:'+repr(min(orbit(raw)))).encode()).hexdigest();train.append(int(f,16)%4!=0)
 ids=np.array(ids);vals=np.array(vals);y=np.array(target);tr=np.array(train);dv=~tr;G=np.zeros((716,716));rhs=np.zeros(716);a=ids[tr];v=vals[tr]
 for i in range(11):
  np.add.at(rhs,a[:,i],v[:,i]*y[tr])
  for j in range(11):np.add.at(G,(a[:,i],a[:,j]),v[:,i]*v[:,j])
 results={};models={}
 for base,size in(('material',2),('kingking',514),('kingpiece',710)):
  for pairs in(False,True):
   name=base+('_pairs'if pairs else'');columns=list(range(size))+(list(range(710,716))if pairs else[]);w=np.zeros(716);w[columns]=np.linalg.solve(G[np.ix_(columns,columns)]+p['ridge']*np.eye(len(columns)),rhs[columns]);pred=(w[ids]*vals).sum(axis=1);res=dict(parameters=len(columns),TRAIN_MSE=float(np.mean((pred[tr]-y[tr])**2)),DEV_MSE=float(np.mean((pred[dv]-y[dv])**2)),DEV_accuracy=float(np.mean(np.where(pred[dv]>.5,1,np.where(pred[dv]<-.5,-1,0))==y[dv])),by_inventory={})
   for inv in('KK','KKN','KKB','KKBN','KKNN','KKBB'):
    mask=dv&np.array([l['inventory']==inv for l in labels]);res['by_inventory'][inv]=dict(n=int(mask.sum()),MSE=float(np.mean((pred[mask]-y[mask])**2)))
   if pairs:res['mechanical_pair_coefficients_WDL_units']={a+'*'+b:float(w[710+k])for k,(a,b)in enumerate(itertools.combinations_with_replacement(('R','N','B'),2))}
   results[name]=res;models[name]=w.tolist()
 result=dict(status='COMPLETE_ALL_SIX_FIXED_MODELS',TRAIN=int(tr.sum()),DEV=int(dv.sum()),models=results,seconds=time.perf_counter()-t,scope=p['scope']+' '+p['split']);assert result['seconds']<p['seconds_cap'];(OUT/'models.json').write_text(json.dumps(models,separators=(',',':')));(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='models'}));print(json.dumps({k:dict(MSE=v['DEV_MSE'],accuracy=v['DEV_accuracy'])for k,v in results.items()}))
if __name__=='__main__':run()

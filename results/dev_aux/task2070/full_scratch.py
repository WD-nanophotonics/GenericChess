"""Cheap full-new-data scratch control and honest zero-shot target accounting."""
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
import json,time
import numpy as np
from results.dev_aux.task2067.transfer import load,arrays,metrics
OUT=Path('results/dev_aux/task2070')
def run():
 t=time.perf_counter();p=json.loads((OUT/'plan.json').read_text());old=load('results/dev_aux/task2058/labels.jsonl');new=load('results/dev_aux/task2065/labels.jsonl');oi,ov,oy,ot,od=arrays(old);ni,nv,ny,nt,nd=arrays(new);prior=json.loads(Path('results/dev_aux/task2067/result.json').read_text());a=ni[nt];v=nv[nt];target=ny[nt];G=np.zeros((710,710));rhs=np.zeros(710)
 for i in range(5):
  np.add.at(rhs,a[:,i],v[:,i]*target)
  for j in range(5):np.add.at(G,(a[:,i],a[:,j]),v[:,i]*v[:,j])
 rows=[];models={};zero={r['model']:r['newDEV']['MSE']for r in prior['curves']if r['method']=='ZERO_SHOT'}
 for name,size in(('material',2),('kingking',514),('kingpiece',710)):
  beg=time.perf_counter();w=np.zeros(710);w[:size]=np.linalg.solve(G[:size,:size]+p['ridge']*np.eye(size),rhs[:size]);fit=time.perf_counter()-beg;newmet=metrics(w,ni,nv,ny,nd);oldmet=metrics(w,oi,ov,oy,od);rows.append(dict(model=name,method='FULL_NEW_TRAIN_CLOSED_FORM_SCRATCH',samples=int(nt.sum()),newDEV=newmet,oldDEV=oldmet,solve_seconds=fit,zero_shot_newDEV_MSE=zero[name],MSE_change_from_zero_shot=newmet['MSE']-zero[name],zero_shot_already_met_target=zero[name]<=.15));models[name]=w.tolist()
 result=dict(status='COMPLETE_NO_MODEL_SELECTION',models=rows,total_including_feature_build_seconds=time.perf_counter()-t,scope='Samewhole-targetteacher alreadycomputed44.73s; all-newTRAINridge ischeap alternative to tuninglimitedSGD. 2067transfer advantage over4epochzeros doesnot prove lowestendtoendcost. ZERO_SHOTmayreachthefixed.15targetwith0newsamples; fine-tune canworsenMSE. Noactualgame/rulesetgeneralstrength claim.')
 assert result['total_including_feature_build_seconds']<p['seconds_cap'];(OUT/'result.json').write_text(json.dumps(result,indent=2));(OUT/'models.json').write_text(json.dumps(models,separators=(',',':')));print(json.dumps(result))
if __name__=='__main__':run()

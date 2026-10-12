"""Whole-training-root price sensitivity, not model selection or confidence interval."""
import json,time,hashlib,importlib.util
from pathlib import Path
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task184';O.mkdir(exist_ok=True)
sp=importlib.util.spec_from_file_location('F184',R/'results/dev_aux/task173/fit.py');M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)
def execute():
 if (O/'analysis.json').exists():raise FileExistsError('frozen')
 started=time.monotonic();M.P.stop();P=R/'results/dev_aux/task169/controller.json';C=json.loads(P.read_bytes());fits=json.loads((R/'results/dev_aux/task173/models.json').read_bytes());train=[]
 for i,c in enumerate(C['calls']):
  if c['context']['phase']!='train':continue
  if i%64==0:M.P.stop()
  r=M.row(c)
  if r is not None:train.append(r)
 results=[];pen=np.diag([0]+[1]*5)
 for source in fits['models']:
  group=[r for r in train if source['opponent']=='pooled' or r['opponent']==source['opponent']];rows=[]
  for removed in range(7):
   use=[r for r in group if r['root_index']!=removed];X=np.asarray([r['features'] for r in use],dtype=float);y=np.asarray([r['targets'][source['target']] for r in use]);beta=np.linalg.solve(X.T@X+pen,X.T@y);positive=bool(np.all(beta[1:]>0));norm={k:float(v/beta[1]) for k,v in zip('PNBRQ',beta[1:])} if abs(beta[1])>1e-12 else None
   rows.append(dict(removed_training_root=removed,n=len(use),coefficients=beta.tolist(),positive_material=positive,Pnormalized=norm,rank=int(np.linalg.matrix_rank(X)),scope='Samefixedlambda1/dataalgorithm, onewholetrainingroot removed, noheldoutread/modelselection ornewtrajectory.'))
  original=source['coefficients'][1:];originalnorm={k:v/original[0] for k,v in zip('PNBRQ',original)}
  results.append(dict(opponent=source['opponent'],target=source['target'],original_Pnormalized=originalnorm,all7_positive=sum(r['positive_material'] for r in rows),Pnormalized_ranges={k:[min(r['Pnormalized'][k] for r in rows if r['Pnormalized'] is not None),max(r['Pnormalized'][k] for r in rows if r['Pnormalized'] is not None)] for k in 'NBRQ'},rows=rows))
 out=dict(complete=True,fits=42,results=results,source_controller_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),seconds=time.monotonic()-started,scope='Exploratory allwhole-training-root deletion sensitivity on alreadyexposedrootfamily. NotformaljackknifeCI/independentmodeldiscovery, nohumanfitting/modelselection/clipping/newenginegames orworkers.')
 (O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(complete=True,fits=42,seconds=out['seconds'],results=[{k:r[k] for k in ('opponent','target','all7_positive','Pnormalized_ranges')} for r in results]),indent=2))
if __name__=='__main__':execute()

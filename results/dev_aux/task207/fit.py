import json,math,time,hashlib,itertools,datetime,importlib.util
from pathlib import Path
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task207';P=R/'results/dev_aux/task187';D=json.loads((O/'declaration.json').read_bytes());sp=importlib.util.spec_from_file_location('S207',R/'results/dev_aux/task166/run.py');M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)
def feature(w):
 z=np.array([2*(math.log(w[k]/208)-math.log(.25))/math.log(64)-1 for k in 'NBRQ']);return [1]+z.tolist()+[float(z[i]*z[j]) for i in range(4) for j in range(i,4)]
def target(c):
 r=c['result'];s=r['score'];out=(0 if s['winner'] is None else (1 if s['winner']==c['context']['agent_color'] else -1)) if s['terminal'] else 0;return [r['bounded_reward'],s['quantity_difference']/15,out]
def execute():
 assert not (O/'models.json').exists();started=time.monotonic();M.stop();C=json.loads((P/'controller.json').read_bytes());train=[c for c in C['calls'] if c['context']['phase']=='train'];X=np.array([feature(c['weights']) for c in train]);Y=np.array([target(c) for c in train]);roots=np.array([c['context']['root_index'] for c in train]);pen=np.diag([0]+[1]*14);models=[]
 grid=[dict(P=208,K=0,**{k:round(208*v) for k,v in zip('NBRQ',z)}) for z in itertools.product((.25,2,16),repeat=4)];Z=np.array([feature(w) for w in grid])
 for j,name in enumerate(D['targets']):
  beta=np.linalg.solve(X.T@X+pen,X.T@Y[:,j]);deletions=[]
  for root in range(8):
   M.stop();keep=roots!=root;bb=np.linalg.solve(X[keep].T@X[keep]+pen,X[keep].T@Y[keep,j]);truth=Y[~keep,j];deletions.append(dict(root=root,n=len(truth),model_mse=float(np.mean((truth-X[~keep]@bb)**2)),trainmean_mse=float(np.mean((truth-np.mean(Y[keep,j]))**2))))
  predictions=Z@beta;best=int(np.argmax(predictions));H=np.zeros((4,4));idx=5
  for i in range(4):
   for k in range(i,4):H[i,k]=H[k,i]=2*beta[idx] if i==k else beta[idx];idx+=1
  models.append(dict(target=name,coefficients=beta.tolist(),hessian_eigenvalues=np.linalg.eigvalsh(H).tolist(),training_mean=float(np.mean(Y[:,j])),training_mse=float(np.mean((Y[:,j]-X@beta)**2)),leave_root_out=deletions,grid_recommendation=grid[best],grid_predicted_value=float(predictions[best]),grid_predictions=[dict(weights=w,prediction=float(p)) for w,p in zip(grid,predictions)]))
 frozen=dict(complete=True,models=models,frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest());(O/'models.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
 held=[c for c in C['calls'] if c['context']['phase']=='heldout'];A=np.array([feature(c['weights']) for c in held]);B=np.array([target(c) for c in held]);results=[]
 for j,m in enumerate(models):
  bet=np.array(m['coefficients']);results.append(dict(target=m['target'],heldout_n=len(held),heldout_mse=float(np.mean((B[:,j]-A@bet)**2)),trainingmean_mse=float(np.mean((B[:,j]-m['training_mean'])**2)),loo_roots_model_better=sum(r['model_mse']<r['trainmean_mse'] for r in m['leave_root_out']),hessian_eigenvalues=m['hessian_eigenvalues'],grid_recommendation=m['grid_recommendation'],grid_predicted_value=m['grid_predicted_value']))
 out=dict(complete=True,train_rows=len(train),results=results,seconds=time.monotonic()-started,scope=D['scope'],decision='No modelrecommendation is actualpolicy/pricelearning evidence; all81gridpredictions kept. Whole-root andexposedendpointerrors decidewhether any new response-surface optimization is warranted.');(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
if __name__=='__main__':execute()

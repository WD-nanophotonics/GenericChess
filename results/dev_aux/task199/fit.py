"""Fixedearly-state return-horizon curve from existingactualgames, no newlabels/games."""
import json,time,datetime,hashlib,importlib.util,math
from pathlib import Path
import chess,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task199';P=R/'results/dev_aux/task187';sp=importlib.util.spec_from_file_location('P199',R/'results/dev_aux/task166/run.py');M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)

def row(c):
 r=c['result'];x=c['context'];b=chess.Board(r['root_fen'])
 for z in r['opening_history']:b.push_uci(z)
 if len(r['actions'])<8:return None
 for z in r['actions'][:8]:b.push_uci(z)
 if b.is_game_over(claim_draw=False):return None
 col=x['agent_color'];features=[1]+[len(b.pieces(i,col))-len(b.pieces(i,not col)) for i in range(1,6)];targets={}
 for h in (2,4,8):
  future=b.copy(stack=True)
  for z in r['actions'][8:8+h]:future.push_uci(z)
  out=future.outcome(claim_draw=False);quantity=sum(len(future.pieces(i,col))-len(future.pieces(i,not col)) for i in range(1,6))/15
  targets[f'quantity_h{h}']=quantity;targets[f'bounded_h{h}']=(0 if out.winner is None else (1 if out.winner==col else -1)) if out else quantity
 return dict(features=features,targets=targets,root=x['root_index'],phase=x['phase'])
def execute():
 assert not (O/'models.json').exists();M.stop();started=time.monotonic();C=json.loads((P/'controller.json').read_bytes());assert C['completed'];train=[];held=[]
 for c in C['calls']:
  if c['context']['phase']=='train':
   r=row(c)
   if r:train.append(r)
 X=np.array([r['features'] for r in train],dtype=float);pen=np.diag([0]+[1]*5);models=[]
 for family in ('quantity','bounded'):
  for h in (2,4,8):
   M.stop();target=f'{family}_h{h}';y=np.array([r['targets'][target] for r in train]);coef=np.linalg.solve(X.T@X+pen,X.T@y);deletions=[]
   for root in range(8):
    mask=np.array([r['root']!=root for r in train]);z=np.linalg.solve(X[mask].T@X[mask]+pen,X[mask].T@y[mask]);norm={k:float(v/z[1]) for k,v in zip('PNBRQ',z[1:])} if abs(z[1])>1e-12 else None;deletions.append(dict(root=root,coefficients=z.tolist(),positive=bool(np.all(z[1:]>0)),Pnormalized=norm))
   models.append(dict(target=target,coefficients=coef.tolist(),root_deletions=deletions,train_mean=float(np.mean(y)),n=len(y)))
 frozen=dict(complete=True,all_models_frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),models=models,source_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest());(O/'models.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
 for c in C['calls']:
  if c['context']['phase']=='heldout':
   r=row(c)
   if r:held.append(r)
 H=np.array([r['features'] for r in held],dtype=float);results=[]
 for model in models:
  y=np.array([r['targets'][model['target']] for r in held]);coef=np.array(model['coefficients']);beta=coef[1:];norm={k:float(v/beta[0]) for k,v in zip('PNBRQ',beta)} if abs(beta[0])>1e-12 else None;results.append(dict(target=model['target'],Pnormalized=norm,positive=bool(np.all(beta>0)),heldout_mse=float(np.mean((y-H@coef)**2)),unitcount_mse=float(np.mean((y-np.sum(H[:,1:],axis=1)/15)**2)),trainmean_mse=float(np.mean((y-model['train_mean'])**2)),root_deletion_positive=sum(z['positive'] for z in model['root_deletions']),root_deletion_ratio_ranges={k:[min(z['Pnormalized'][k] for z in model['root_deletions']),max(z['Pnormalized'][k] for z in model['root_deletions'])] for k in 'NBRQ'}))
 out=dict(complete=True,train_rows=len(train),heldout_rows=len(held),results=results,seconds=time.monotonic()-started,scope='Samefixed8plycount features and alltrajectorydistribution, returnlag2/4/8.9originalfitdataexposed; fixedlambda, whole-rootheldouts/deletions. No newgame/teacher/humanfitting, no causal horizonproof/extrapolation tolonggames/policygain. Earlyterminal preserves actualoutcome, nofictitiouscontinuation.');(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
if __name__=='__main__':execute()

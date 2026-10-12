import json,math,time,hashlib,datetime
from pathlib import Path
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task218';D=json.loads((O/'declaration.json').read_bytes());P=R/'results/dev_aux/task214/controller.json'
def execute():
 assert not (O/'models.json').exists();assert hashlib.sha256(P.read_bytes()).hexdigest()==D['source_sha256'];C=json.loads(P.read_bytes());started=time.monotonic();models=[]
 for seed in D['seeds']:
  source=next(r for r in C['runs'] if r['seed']==seed and r['mode']=='fixed_teacher')
  for lam in D['lambdas']:
   theta=np.array(source['initial_theta']);rounds=[]
   for z in source['rounds']:
    targets={};tail=0;terminal=0
    for r in reversed(z['all_transitions']):
     key=(r['game'],r['index']);nxt=(r['game'],r['index']+1)
     if r['target_kind']=='true_terminal':targets[key]=r['target'];terminal+=1
     elif nxt in targets:targets[key]=(1-lam)*r['target']+lam*targets[nxt]
     else:targets[key]=r['target'];tail+=1
    updates=[]
    for r in z['all_transitions']:
     key=(r['game'],r['index']);phi=np.array(r['features'],dtype=float);ratios=np.exp(theta);v=math.tanh((phi[0]+np.dot(phi[1:],ratios))/4);grad=(1-v*v)/4*phi[1:]*ratios;y=targets[key];delta=y-v;alpha=D['alpha']/max(1,float(grad@grad));before=theta.copy();theta=np.clip(theta+alpha*delta*grad,math.log(.25),math.log(16));vv=math.tanh((phi[0]+np.dot(phi[1:],np.exp(theta)))/4);updates.append(dict(game=r['game'],index=r['index'],target=y,lambda0target=r['target'],target_kind=r['target_kind'],features=r['features'],before=before.tolist(),after=theta.tolist(),value=v,gradient=grad.tolist(),alpha=alpha,loss_before=(y-v)**2,loss_after=(y-vv)**2))
    rounds.append(dict(round=z['round'],teacher_weights=z['teacher_weights'],real_terminal_rows=terminal,qualified_tail_or_gap_fallbacks=tail,excluded=z['excluded'],updates=updates))
   weights=dict(P=208,K=0,**{k:round(208*math.exp(t)) for k,t in zip('NBRQ',theta)})
   if lam==0:assert np.max(abs(theta-np.array(source['final_theta'])))<1e-12 and weights==source['final_weights']
   models.append(dict(seed=seed,lambda_return=lam,initial_weights=source['initial_weights'],initial_theta=source['initial_theta'],final_weights=weights,final_theta=theta.tolist(),rounds=rounds,shadow=True))
 out=dict(complete=True,all9models_frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),models=models,seconds=time.monotonic()-started,lambda0_exact_rounding_control=True,source_sha256=D['source_sha256'],scope=D['scope']);(O/'models.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(models=9,seconds=out['seconds'],lambda0matched=True,prices=[dict(seed=m['seed'],lambda_return=m['lambda_return'],weights=m['final_weights']) for m in models]),indent=2))
if __name__=='__main__':execute()

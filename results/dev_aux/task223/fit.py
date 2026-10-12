import json,math,time,datetime,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task223';D=json.loads((O/'declaration.json').read_bytes());P=R/'results/dev_aux/task214/controller.json';assert hashlib.sha256(P.read_bytes()).hexdigest()==D['source_sha256'];C=json.loads(P.read_bytes());started=time.monotonic();models=[]
for seed in D['seeds']:
 src=next(z for z in C['runs'] if z['seed']==seed and z['mode']=='fixed_teacher');theta=list(src['initial_theta']);updates=[];excluded=[];completed=[]
 for c in C['calls']:
  q=c['context'];r=c['result'];s=r['score']
  if q['phase']!='train' or q['seed']!=seed or q['mode']!='fixed_teacher':continue
  if not s['terminal']:excluded.append(q['name']);continue
  completed.append(dict(game=q['name'],termination=s['termination'],winner=s['winner'],actor=r['agent_color']));y=0 if s['winner'] is None else (1 if s['winner']==r['agent_color'] else -1)
  for z in r['root_features']:
   f=z['features_actor'];v=math.tanh((f[0]+sum(a*math.exp(t) for a,t in zip(f[1:],theta)))/4);g=[(1-v*v)*a*math.exp(t)/4 for a,t in zip(f[1:],theta)];alpha=.02/max(1,sum(t*t for t in g));before=theta[:];theta=[min(math.log(16),max(math.log(.25),t+alpha*(y-v)*gg)) for t,gg in zip(theta,g)];vv=math.tanh((f[0]+sum(a*math.exp(t) for a,t in zip(f[1:],theta)))/4);updates.append(dict(game=q['name'],ply=z['ply'],features=f,target=y,before=before,after=theta[:],value=v,gradient=g,alpha=alpha,loss_before=(y-v)**2,loss_after=(y-vv)**2))
 weights=dict(P=208,K=0,**{k:round(208*math.exp(t)) for k,t in zip('NBRQ',theta)});models.append(dict(seed=seed,initial_weights=src['initial_weights'],initial_theta=src['initial_theta'],final_weights=weights,final_theta=theta,updates=updates,completed=completed,excluded_unknown_games=excluded))
out=dict(complete=True,models=models,seconds=time.monotonic()-started,all_models_frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=D['source_sha256'],scope=D['scope']);(O/'models.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(seed=m['seed'],weights=m['final_weights'],updates=len(m['updates']),completed=len(m['completed']),unknown=len(m['excluded_unknown_games'])) for m in models]))

import json,math,time,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task221';O.mkdir(exist_ok=True)
D=json.loads((R/'results/dev_aux/task218/declaration.json').read_bytes());C=json.loads((R/'results/dev_aux/task214/controller.json').read_bytes());X=json.loads((R/'results/dev_aux/task218/models.json').read_bytes());started=time.monotonic();rows=0;loss_increases=0;stats=[]
for m in X['models']:
 src=next(s for s in C['runs'] if s['seed']==m['seed'] and s['mode']=='fixed_teacher');theta=list(src['initial_theta']);lam=m['lambda_return'];terminal=tail=propagated=0
 for z,fitted in zip(src['rounds'],m['rounds']):
  by_game={}
  for r in z['all_transitions']:by_game.setdefault(r['game'],{})[r['index']]=r
  targets={}
  for game,rs in by_game.items():
   for i in sorted(rs,reverse=True):
    r=rs[i]
    if r['target_kind']=='true_terminal': y=r['target'];terminal+=1
    elif (game,i+1) in targets:y=(1-lam)*r['target']+lam*targets[game,i+1];propagated+=1
    else:y=r['target'];tail+=1
    targets[game,i]=y
  assert fitted['excluded']==z['excluded'] and fitted['teacher_weights']==z['teacher_weights']
  for r,u in zip(z['all_transitions'],fitted['updates']):
   assert r['game']==u['game'] and r['index']==u['index'];y=targets[r['game'],r['index']];assert abs(y-u['target'])<1e-12
   f=r['features'];ratios=[math.exp(t) for t in theta];v=math.tanh((f[0]+sum(a*b for a,b in zip(f[1:],ratios)))/4);g=[(1-v*v)*a*b/4 for a,b in zip(f[1:],ratios)];alpha=.02/max(1,sum(t*t for t in g))
   assert max(abs(a-b) for a,b in zip(theta,u['before']))<1e-12
   assert abs(v-u['value'])<1e-12 and max(abs(a-b) for a,b in zip(g,u['gradient']))<1e-12 and abs(alpha-u['alpha'])<1e-12
   theta=[min(math.log(16),max(math.log(.25),t+alpha*(y-v)*gg)) for t,gg in zip(theta,g)]
   assert max(abs(a-b) for a,b in zip(theta,u['after']))<1e-12
   vv=math.tanh((f[0]+sum(a*math.exp(t) for a,t in zip(f[1:],theta)))/4);l0=(y-v)**2;l1=(y-vv)**2
   assert abs(l0-u['loss_before'])<1e-12 and abs(l1-u['loss_after'])<1e-12;loss_increases+=l1>l0+1e-12;rows+=1
  assert len(fitted['updates'])==len(z['all_transitions'])
 assert max(abs(a-b) for a,b in zip(theta,m['final_theta']))<1e-12
 assert dict(P=208,K=0,**{k:round(208*math.exp(t)) for k,t in zip('NBRQ',theta)})==m['final_weights']
 if lam==0:assert m['final_weights']==src['final_weights'] and max(abs(a-b) for a,b in zip(theta,src['final_theta']))<1e-12
 stats.append(dict(seed=m['seed'],lambda_return=lam,actual_terminal_rows=terminal,fallback_rows=tail,propagated_rows=propagated))
out=dict(complete=True,models=len(X['models']),updates=rows,fixed_target_loss_increases=loss_increases,lambda0_all3_exact=True,stats=stats,seconds=time.monotonic()-started,scope='Independent scalar recurrence and semigradient replay; stopgradient targets retained; lambda1 unknown tails/gaps still use teacher forecasts; not full MonteCarlo or new onpolicy learning.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))

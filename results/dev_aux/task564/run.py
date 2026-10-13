import sys,json,time,hashlib,math,os
from pathlib import Path
from fractions import Fraction
R=Path.cwd();D=R/'results/dev_aux/task564/declaration.json';d=json.loads(D.read_bytes())
for n in [360,364,381,509,547]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V,controller as N24
sys.path.insert(0,str(R/'results/dev_aux/task564'));import controller12 as N
from warm_adapter import ControlledEngine
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];train=[f for f in d['roots'] if f['phase']=='train'];dev=[f for f in d['roots'] if f['phase']=='development'];t0=time.monotonic();remaining=d['fuse']-(time.time()-d['frozen_at']);assert remaining>0;deadline=t0+remaining;contexts={};axes=d['axes']
def save(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf-8')
def batch(ctx,w,roots,qj,gj,eu):
 G.stop();assert time.monotonic()<deadline;ec=ControlledEngine(w,qj,'warm_game');ctx['acks'].append(dict(role='candidate',weights=list(w),prices=ec.prices));save(ctx['folder']/'price_acks.json',ctx['acks']);refs=[];gs=[]
 try:
  for f in roots:
   for c in (0,1):
    ec.begin_game();eu.begin_game() if eu else None;g=N.native_game(ec,eu,w,f,c,gj,d,deadline);ctx['games']+=1;ctx['go']+=len(g['queries']);ref=dict(file=ctx['folder'].relative_to(R).as_posix()+'/games.jsonl',line=ctx['games']);refs.append(ref);gs.append(dict(goal=g['goal'],qty=g['raw_quantity'],winner=g['termination']['winner'],kind=g['termination']['kind'],color=c))
 finally:ec.close()
 goals=[g['goal'] for g in gs]
 return dict(objective='mixed_cap12' if d['cap']==12 else 'physical_mixed_cap24',weights=list(w),mean_goal=str(sum(map(Fraction,goals))/len(gs)),mean_quantity=str(sum(Fraction(g['qty']) for g in gs)/len(gs)),goals=goals,physical_goals=[g['goal'] for g in gs],sources=refs,true_wins=sum(g['winner']==g['color'] for g in gs),true_losses=sum(g['winner'] is not None and g['winner']!=g['color'] for g in gs),rule_outcomes=[g['kind'] for g in gs])
for opp,task in [('unit',565),('random',566)]:
 O=R/f'results/dev_aux/task{task}';O.mkdir(exist_ok=True);assert not (O/'games.jsonl').exists();ctx=dict(folder=O,games=0,go=0,updates=[],endpoints=[],acks=[]);contexts[opp]=ctx;start=time.monotonic()
 with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
  eu=ControlledEngine(d['fixed_opponent'],qj,'warm_game') if opp=='unit' else None
  if eu:ctx['acks'].append(dict(role='unit',weights=eu.w,prices=eu.prices));save(O/'price_acks.json',ctx['acks'])
  try:
   for p in d['initial_profiles']:
    w=list(p['weights']);base=batch(ctx,w,train,qj,gj,eu)
    for i,di in enumerate(d['directions'][p['name']]):
     startw=list(w);plus=list(w);minus=list(w)
     for a,s in zip(axes,di):plus[a]=max(32,min(4096,math.floor(w[a]*math.exp(.25*s)+.5)));minus[a]=max(32,min(4096,math.floor(w[a]*math.exp(-.25*s)+.5)))
     cs=[base,batch(ctx,plus,train,qj,gj,eu),batch(ctx,minus,train,qj,gj,eu)];means=list(map(lambda x:Fraction(x['mean_goal']),cs));best=max(range(3),key=lambda j:means[j]);gain=means[best]-means[0]
     if gain>0:w=list(cs[best]['weights']);base=cs[best]
     else:best=0
     ctx['updates'].append(dict(family=p['name'],iteration=i,direction=di,start_weights=startw,candidates=cs,selected_index=best,accepted_strict_gain=str(gain),after_weights=list(w),changed_integer_axes=sum(startw[a]!=w[a] for a in axes)));save(O/'progress.json',dict(updates=ctx['updates'],new_games=ctx['games'],new_go=ctx['go'],seconds=time.monotonic()-start));print(opp,p['name'],i,str(gain),ctx['games'],round(time.monotonic()-t0,1),flush=True)
    ctx['endpoints'].append(dict(family=p['name'],initial=p['weights'],endpoint=w,iterations=24))
  finally:eu.close() if eu else None
 save(O/'endpoints.json',dict(opponent=opp,all_endpoints_before_development=True,declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),endpoints=ctx['endpoints'],updates=ctx['updates'],fit_new_games=ctx['games'],fit_new_go=ctx['go'],fit_seconds=time.monotonic()-start));save(O/'result.json',dict(status='FIT_COMPLETE',opponent=opp,actual_games=ctx['games'],actual_go=ctx['go'],seconds=time.monotonic()-start,endpoints=ctx['endpoints']))
freeze=dict(before_any_development=True,declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),endpoint_sha256={opp:hashlib.sha256((ctx['folder']/'endpoints.json').read_bytes()).hexdigest() for opp,ctx in contexts.items()},seconds=time.monotonic()-t0);save(R/'results/dev_aux/task564/all_endpoints_frozen.json',freeze)
profiles=[]
for opp,ctx in contexts.items():
 for e in ctx['endpoints']:
  for stage,w in [('endpoint',e['endpoint'])]:
   if not any(p['weights']==w for p in profiles):profiles.append(dict(weights=w,names=[]))
   next(p for p in profiles if p['weights']==w)['names'].append(opp+'-'+e['family']+'-'+stage)
d['cap']=24;N=N24
O=R/'results/dev_aux/task567';O.mkdir(exist_ok=True);assert not (O/'games.jsonl').exists();ctx=dict(folder=O,games=0,go=0,acks=[]);rows=[]
with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
 for p in profiles:
  for opp in d['opponents']:
   eu=ControlledEngine(d['fixed_opponent'],qj,'warm_game') if opp=='unit' else None
   if eu:ctx['acks'].append(dict(role='unit',weights=eu.w,prices=eu.prices))
   try:row=batch(ctx,p['weights'],dev,qj,gj,eu);rows.append(dict(names=p['names'],opponent=opp,batch=row));print('development',p['names'],opp,ctx['games'],round(time.monotonic()-t0,1),flush=True)
   finally:eu.close() if eu else None
save(O/'result.json',dict(status='COMPLETE',profiles=profiles,rows=rows,actual_games=ctx['games'],actual_go=ctx['go'],seconds=time.monotonic()-t0,training_games=sum(c['games'] for c in contexts.values()),training_go=sum(c['go'] for c in contexts.values()),endpoint_freeze=freeze,scope=d['scope']));print('COMPLETE',round(time.monotonic()-t0,1),flush=True)

import sys,json,time,hashlib,math,random,os
from pathlib import Path
from fractions import Fraction
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G;sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
A.EXE=R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe';A.validate_search=V.query
D=R/'results/dev_aux/task417/declaration.json';d=json.loads(D.read_text(encoding='utf-8'));assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];d['seed_base']=d['random_seed_base'];t0=time.monotonic();axes=d['axes'];train=[f for f in d['roots'] if f['phase']=='train'];dev=[f for f in d['roots'] if f['phase']=='development']
# Copy only the immutable function body, NOT task410 producer top-level.
src=(R/'results/dev_aux/task410/run_random.py').read_text(encoding='utf-8');src=src[src.index('def random_game('):src.index("arm=sys.argv[1]")]
src=src.replace("d['seed_base']+2*f['index']+c","d['seed_base']+2*f['index']+c+(100 if f['phase']=='development' else 0)")
exec(compile(src,'frozen_random_controller','exec'))
contexts={}
def batch(ctx,w,roots,qj,gj,eu):
 rows=[];refs=[];missing=any((tuple(w),f['phase'],f['index'],c) not in ctx['cache'] for f in roots for c in (0,1));ec=A.Engine(w,qj) if missing else None
 if ec:ctx['acks'].append(dict(weights=w,prices=ec.prices))
 try:
  for f in roots:
   for c in (0,1):
    ctx['logical']+=1;k=(tuple(w),f['phase'],f['index'],c)
    if k in ctx['cache']:g,ref=ctx['cache'][k];ctx['hits']+=1
    else:
     g=G.game(ec,eu,w,f,c,gj,cap=d['cap'],nodes=d['nodes'],deadline=t0+1800) if eu else random_game(ec,w,f,c,gj,t0+1800);ctx['games']+=1;ctx['go']+=len(g['queries']);ref=dict(file=ctx['folder'].relative_to(R).as_posix()+'/games.jsonl',line=ctx['games']);ctx['cache'][k]=(g,ref)
    rows.append(g);refs.append(ref)
 finally:
  if ec:ec.close()
 return dict(weights=list(w),mean_goal=str(sum((Fraction(g['goal']) for g in rows),Fraction())/len(rows)),mean_quantity=str(sum(Fraction(g['raw_quantity']) for g in rows)/len(rows)),goals=[g['goal'] for g in rows],sources=refs,true_wins=sum(g['termination']['winner']==g['color'] for g in rows),true_losses=sum(g['termination']['winner'] is not None and g['termination']['winner']!=g['color'] for g in rows))
for arm,task in [('unit',418),('random',419)]:
 O=R/f'results/dev_aux/task{task}';O.mkdir(exist_ok=True);assert not (O/'games.jsonl').exists();ctx=dict(folder=O,cache={},acks=[],logical=0,hits=0,games=0,go=0,updates=[],endpoints=[],diagnostics=[]);contexts[arm]=ctx;armstart=time.monotonic()
 with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
  eu=A.Engine(d['fixed_opponent'],qj) if arm=='unit' else None
  try:
   for p in d['initial_profiles']:
    initial=list(p['weights']);w=list(initial);base=batch(ctx,w,train,qj,gj,eu)
    for iteration,direction in enumerate(d['directions'][p['name']]):
     start=list(w);plus=list(w);minus=list(w)
     for axis,sign in zip(axes,direction):
      plus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(.25*sign)+.5)));minus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(-.25*sign)+.5)))
     cs=[base,batch(ctx,plus,train,qj,gj,eu),batch(ctx,minus,train,qj,gj,eu)];scores=[Fraction(x['mean_goal']) for x in cs];best=max(range(3),key=lambda j:scores[j]);gain=scores[best]-scores[0]
     if gain>0:w=list(cs[best]['weights']);base=cs[best]
     else:best=0
     ctx['updates'].append(dict(family=p['name'],iteration=iteration,direction=direction,start_weights=start,candidates=cs,selected_index=best,accepted_strict_gain=str(gain),after_weights=list(w),changed_integer_axes=sum(start[a]!=w[a] for a in axes)));(O/'progress.json').write_text(json.dumps(dict(updates=ctx['updates'],new_games=ctx['games'],new_go=ctx['go'],seconds=time.monotonic()-armstart),indent=2),encoding='utf-8');print(arm,p['name'],iteration,str(gain),ctx['games'],round(time.monotonic()-t0),flush=True)
    ctx['endpoints'].append(dict(method='joint',family=p['name'],initial=initial,endpoint=list(w),iterations=24))
  finally:
   if eu:eu.close()
 ctx['fit_seconds']=time.monotonic()-armstart;ctx['fit_games']=ctx['games'];ctx['fit_go']=ctx['go'];ctx['fit_logical']=ctx['logical'];ctx['fit_hits']=ctx['hits']
 (O/'endpoints.json').write_text(json.dumps(dict(arm=arm,frozen_before_development=True,declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),endpoints=ctx['endpoints'],updates=ctx['updates'],rounds=[],fit_new_games=ctx['games'],fit_new_go=ctx['go'],fit_logical_games=ctx['logical'],fit_cache_hits=ctx['hits'],fit_seconds=ctx['fit_seconds']),indent=2),encoding='utf-8')
# BOTH arms end records written BEFORE opening ANY development query.
freeze=dict(declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),both_endpoints={a:hashlib.sha256((c['folder']/'endpoints.json').read_bytes()).hexdigest() for a,c in contexts.items()},before_any_development=True,seconds=time.monotonic()-t0);(R/'results/dev_aux/task417/all_endpoints_frozen.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
for arm,ctx in contexts.items():
 O=ctx['folder'];profiles=[]
 for e in ctx['endpoints']:
  for stage,w in [('initial',e['initial']),('endpoint',e['endpoint'])]:
   if not any(x['weights']==w for x in profiles):profiles.append(dict(weights=w,names=[]))
   next(x for x in profiles if x['weights']==w)['names'].append(e['method']+'-'+e['family']+'-'+stage)
 with (O/'queries.jsonl').open('a',encoding='utf-8') as qj,(O/'games.jsonl').open('a',encoding='utf-8') as gj:
  eu=A.Engine(d['fixed_opponent'],qj) if arm=='unit' else None
  try:
   for phase,roots in [('train_endpoint_diagnostic',train),('development',dev)]:
    for p in profiles:
     row=batch(ctx,p['weights'],roots,qj,gj,eu);row.update(phase=phase,names=p['names']);ctx['diagnostics'].append(row);print(arm,phase,p['names'],row['mean_goal'],flush=True)
  finally:
   if eu:eu.close()
 (O/'price_acks.json').write_text(json.dumps(ctx['acks'],indent=2),encoding='utf-8');out=dict(arm=arm,status='completed',fit_seconds=ctx['fit_seconds'],fit_new_games=ctx['fit_games'],fit_new_go=ctx['fit_go'],fit_logical_games=ctx['fit_logical'],fit_cache_hits=ctx['fit_hits'],new_games=ctx['games'],new_go=ctx['go'],logical_games=ctx['logical'],cache_hits=ctx['hits'],endpoints=ctx['endpoints'],diagnostics=ctx['diagnostics']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('COMPLETE',arm,{k:v for k,v in out.items() if k not in ['endpoints','diagnostics']},flush=True)
(R/'results/dev_aux/task417/completed.json').write_text(json.dumps(dict(seconds=time.monotonic()-t0,status='completed',total_new_games=sum(c['games'] for c in contexts.values()),total_new_go=sum(c['go'] for c in contexts.values())),indent=2),encoding='utf-8')

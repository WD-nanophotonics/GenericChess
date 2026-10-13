import sys,json,time,hashlib,math,random,os
from pathlib import Path
from fractions import Fraction
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G;sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';A.validate_search=V.query
D=R/'results/dev_aux/task532/declaration.json';d=json.loads(D.read_text(encoding='utf-8'));assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];d['seed_base']=d['random_seed_base'];t0=time.monotonic();axes=d['axes'];train=[f for f in d['roots'] if f['phase']=='train'];dev=[f for f in d['roots'] if f['phase']=='development']
# Copy only the immutable function body, NOT task410 producer top-level.
src=(R/'results/dev_aux/task410/run_random.py').read_text(encoding='utf-8');src=src[src.index('def random_game('):src.index("arm=sys.argv[1]")]
src=src.replace("d['seed_base']+2*f['index']+c","d['seed_base']+2*f['index']+c+(100 if f['phase']=='development' else 0)")
src=src.replace('out=dict(weights=w','out=dict(reset_policy=current_policy,weights=w')
exec(compile(src,'frozen_random_controller','exec'))
sys.path.insert(0,str(R/'results/dev_aux/task509'));from warm_adapter import ControlledEngine
current_policy='warm_game';current_objective='pure_terminal';A.Engine=lambda w,journal=None:ControlledEngine(w,journal,current_policy)
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
     ec.begin_game();eu.begin_game() if eu else None
     if eu:
      g=G.game(ec,eu,w,f,c,None,cap=d['cap'],nodes=d['nodes'],deadline=t0+3300);g.update(reset_policy=current_policy);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno())
     else:g=random_game(ec,w,f,c,gj,t0+3300)
     ctx['games']+=1;ctx['go']+=len(g['queries']);ref=dict(file=ctx['folder'].relative_to(R).as_posix()+'/games.jsonl',line=ctx['games']);ctx['cache'][k]=(g,ref)
    rows.append(g);refs.append(ref)
 finally:
  if ec:ec.close()
 goals=[g['goal'] if current_objective=='mixed' else str(0 if g['termination']['winner'] is None else (32 if g['termination']['winner']==g['color'] else -32)) for g in rows]
 return dict(objective=current_objective,weights=list(w),mean_goal=str(sum(map(Fraction,goals),Fraction())/len(rows)),mean_quantity=str(sum(Fraction(g['raw_quantity']) for g in rows)/len(rows)),goals=goals,physical_goals=[g['goal'] for g in rows],sources=refs,true_wins=sum(g['termination']['winner']==g['color'] for g in rows),true_losses=sum(g['termination']['winner'] is not None and g['termination']['winner']!=g['color'] for g in rows))
for condition in d['fit_conditions']:
 arm=condition['name'];task=condition['task']
 current_objective='pure_terminal';current_policy='warm_game';A.EXE=R/('.local_agent/yaneura27/yaneura-material1-hand-see.exe' if arm=='cold_per_query' else '.local_agent/yaneura27/yaneura-material1-hand-see.exe');assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];d['nodes']=condition['nodes'];O=R/f'results/dev_aux/task{task}';O.mkdir(exist_ok=True);assert not (O/'games.jsonl').exists();ctx=dict(folder=O,cache={},acks=[],logical=0,hits=0,games=0,go=0,updates=[],endpoints=[],diagnostics=[]);contexts[arm]=ctx;armstart=time.monotonic()
 with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
  eu=A.Engine(d['fixed_opponent'],qj) if condition['opponent']=='unit' else None
  if eu:ctx['acks'].append(dict(role='unit',weights=eu.w,prices=eu.prices))
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
# Both fit endpoint records precede ANY development game/endpointevaluation.
freeze=dict(declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),both_endpoints={a:hashlib.sha256((c['folder']/'endpoints.json').read_bytes()).hexdigest() for a,c in contexts.items()},before_any_development=True,seconds=time.monotonic()-t0);(R/'results/dev_aux/task532/all_endpoints_frozen.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
for arm,ctx in contexts.items():
 O=ctx['folder'];(O/'price_acks.json').write_text(json.dumps(ctx['acks'],indent=2),encoding='utf-8');out=dict(arm=arm,status='fit_completed',fit_seconds=ctx['fit_seconds'],fit_new_games=ctx['fit_games'],fit_new_go=ctx['fit_go'],fit_logical_games=ctx['fit_logical'],fit_cache_hits=ctx['fit_hits'],new_games=ctx['games'],new_go=ctx['go'],logical_games=ctx['logical'],cache_hits=ctx['hits'],endpoints=ctx['endpoints']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
profiles=[]
for arm,ctx in contexts.items():
 for e in ctx['endpoints']:
  for stage,w in [('initial',e['initial']),('endpoint',e['endpoint'])]:
   if not any(p['weights']==w for p in profiles):profiles.append(dict(weights=w,names=[]))
   next(p for p in profiles if p['weights']==w)['names'].append(arm+'-trained-'+e['family']+'-'+stage)
O=R/'results/dev_aux/task537';O.mkdir(exist_ok=True);assert not(O/'games.jsonl').exists();rows=[];acks=[];go=0;newgames=0
# Tag before the real random game's final journal write; no fabricated random go.
randomsrc=src.replace('out=dict(reset_policy=current_policy,weights=w', "out=dict(reset_policy=current_policy,engine_arm=searcharm,opponent_arm='random',nodes_limit=d['nodes'],weights=w")
exec(compile(randomsrc,'tagged_future_random','exec'))
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for searcharm in ['warm_game']:
  current_policy=searcharm;A.EXE=R/('.local_agent/yaneura27/yaneura-material1-hand-see.exe' if searcharm=='cold_per_query' else '.local_agent/yaneura27/yaneura-material1-hand-see.exe');assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256']
  for budget in d['development_node_budgets']:
   d['nodes']=budget
   for env in d['development_environments']:
    eu=A.Engine(d['fixed_opponent'],qj) if env=='unit' else None
    try:
     for p in profiles:
      ec=A.Engine(p['weights'],qj);acks.append(dict(engine_arm=searcharm,weights=ec.w,prices=ec.prices,nodes=budget,opponent=env))
      try:
       for f in dev:
        for c in (0,1):
         ec.begin_game();eu.begin_game() if eu else None
         g=G.game(ec,eu,p['weights'],f,c,None,cap=d['cap'],nodes=budget,deadline=t0+3300) if eu else random_game(ec,p['weights'],f,c,gj,t0+3300)
         if eu:g.update(reset_policy=current_policy,engine_arm=searcharm,opponent_arm=env,nodes_limit=budget);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno())
         newgames+=1;go+=len(g['queries']);rows.append(dict(engine_arm=searcharm,nodes=budget,opponent=env,names=p['names'],weights=p['weights'],root_index=f['index'],color=c,goal=g['goal'],quantity=g['raw_quantity'],termination=g['termination'],plies=len(g['actions']),source=dict(file='results/dev_aux/task537/games.jsonl',line=newgames)))
      finally:ec.close()
    finally:
     if eu:eu.close()
r=dict(status='completed',seconds=time.monotonic()-t0,new_games=newgames,new_go=go,rows=rows,profiles=profiles,price_acks=acks);(O/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print('COMPLETE',newgames,go,r['seconds'])

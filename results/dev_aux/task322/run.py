"""Bounded coordinate material learning on dense true random-mate speed, no human fit."""
import json,time,sys,math,os,importlib.util,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();sp=importlib.util.spec_from_file_location('G320',R/'results/dev_aux/task320/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task322';O.mkdir(exist_ok=False);Q.P.stop();pilotD=json.loads((R/'results/dev_aux/task320/declaration.json').read_bytes());pilot=json.loads((R/'results/dev_aux/task320/result.json').read_bytes());roots=pilotD['roots'];D=dict(task_id='322',initials=pilotD['profiles'],roots=roots,colors=[True,False],random_seeds=list(range(2026102301,2026102317)),max_rounds_per_initial=6,node_limit=1024,cap=48,step='PNBRQ P=208K0fixed; 9candidates:base thenN/B/R/Q half/double, nearestinteger usingexactpositive rounding, clip32..8192 predeclaredsearchdomain. Equalfitnessretainbase; amongstrictpositivebesttie orderedN-/N+/B-/B+/R-/R+/Q-/Q+. Stopfamilyfirstno strictimprovement; noforcedremainingrounds.',goal=pilotD['fitness'],whole_fuse_seconds=2400,projected_upper_seconds=pilot['seconds']/24*(3*6*9*64),cost_reason='24pilot4.735s and23true mates showdensecheapgoal. 2seedpairedvariability/profile mixeddirection suggests4seedfitnessstillfragile; BEFORElearner freezes16seeds/64cells perprice toreduce stochasticselectionnoise. Cacheidenticalprice+root/color/seed/node/cap inputs; noresult-drivenseed/horizongrowth. Max10368logicalgameevaluationsbeforecache/plateaustop, projection34min; singlebatchunderhour with40minfuse andnoextensions. Noextra workers/fees.',qualification='Everycandidatefreshprocess; config272supports32..8192 withfiveleafandexactMG/EGack; ucinewgameeverygo/coldTT; fullhistory+actualqueries persisted.',pilot_reuse='24alreadyqualified320games sameinputs amongfirst2seeds, reusednotnew.',development='OnlyafterALL3endpoints frozen, use2oldexposeddevelopmentroots,bothcolors,NEWfixed4seeds2026102391..2394 atsame1024/cap48. Baselines+endpointsatmost6uniqueprices/96games. Distinctroottransferdiagnostic; sourcepositionsnotfreshholdout. Notreadbeforefit/endpoints.',interpretation='Learnsgoal-specificmaterialvector forrandomopponent/mate-speed, not strength/finalWDL. HumanreferenceonlyAFTERfrozenendpointfor descriptiveagreement; no selection, penalties, coefficientpriors orterminationruleusinghuman. Root/color/seedgroupdiagnostics zeronewgames, no bestfold/endpointadoption. EarlierOLS/269failures retained; changedgoal+opponentnotreplication.',source_hashes={str(p.relative_to(R)):Q.sha(p) for p in [R/'results/dev_aux/task320/result.json',R/'results/dev_aux/task321/audit.json',R/'results/dev_aux/task272/configure.py']})
Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+2400;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(),'configure272','exec'),env);configure=env['configure'];cache={};actual_games=0;actual_queries=0;reused=0;history=[];endpoints={};evaluations=[];status=dict(complete=False)
def key(w,root,color,seed):return (tuple(w[k] for k in 'PNBRQK'),root,color,seed)
for z in pilot['calls']:cache[key(z['weights'],z['root'],z['color'],z['seed'])]=dict(z,source='320')
def save():Q.write(O/'progress.json',dict(actual_games=actual_games,actual_queries=actual_queries,cache_reuses=reused,unique_cases=len(cache),rounds=history,endpoints=endpoints,seconds=time.monotonic()-start,status=status))
with (O/'games.jsonl').open('x',encoding='utf-8') as games,(O/'queries.jsonl').open('x',encoding='utf-8') as journal:
 def evaluate(w,name):
  global actual_games,actual_queries,reused
  e=None;rows=[]
  try:
   for ri,f in enumerate(roots):
    for color in D['colors']:
     for seed in D['random_seeds']:
      kk=key(w,ri,color,seed)
      if kk in cache:row=cache[kk];reused+=1
      else:
       Q.P.A.guard(deadline,Q.P.stop)
       if e is None:e=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
       journal.write(json.dumps(dict(event='game_start',name=name,root=ri,color=color,seed=seed,weights=w),separators=(',',':'))+'\n');journal.flush();row=dict(name=name,root=ri,source='322',**G.run_game(e,w,f,color,seed,1024,deadline,configure,journal=journal));actual_queries+=len(row['search_records']);actual_games+=1;cache[kk]=row;games.write(json.dumps(row,separators=(',',':'))+'\n');games.flush();os.fsync(games.fileno())
      rows.append(row)
  finally:
   if e:e.close()
  mean=sum(F(z['fitness']) for z in rows)/len(rows);entry=dict(name=name,weights=w,mean_fitness=str(mean),wins=sum(z['finite_mate_sign']==1 for z in rows),losses=sum(z['finite_mate_sign']==-1 for z in rows),unknown=sum(z['termination']=='UNKNOWN_CUTOFF' for z in rows));evaluations.append(entry);Q.write(O/'evaluations.json',evaluations);save();return mean,entry
 try:
  for family,initial in D['initials'].items():
   current=initial.copy();path=[];ending='max_rounds'
   for generation in range(6):
    candidates=[('base',current)]
    for k in 'NBRQ':
     for sign in ('-','+'):
      w=current.copy();w[k]=max(32,min(8192,(w[k]+1)//2 if sign=='-' else 2*w[k]));candidates.append((k+sign,w))
    scores=[]
    for variant,w in candidates:
     v,entry=evaluate(w,f'{family}-g{generation}-{variant}');scores.append((v,variant,w));print(family,generation,variant,str(v),actual_games,round(time.monotonic()-start,2),flush=True)
    chosen=max(scores,key=lambda z:z[0]);row=dict(family=family,generation=generation,starting=current,selected=chosen[1],weights=chosen[2],baseline_fitness=str(scores[0][0]),selected_fitness=str(chosen[0]),strict_gain=chosen[0]>scores[0][0],candidates=[dict(variant=nm,weights=w,fitness=str(v)) for v,nm,w in scores]);history.append(row);path.append(row);current=chosen[2].copy();save()
    if not row['strict_gain']:ending='no_strict_coordinate_improvement';break
   endpoints[family]=dict(weights=current,rounds=len(path),ending=ending,fitness=path[-1]['selected_fitness']);save()
  # Endpoint file is immutable and saved before ANY development position/target is used.
  Q.write(O/'endpoints.json',dict(complete=True,endpoints=endpoints,frozen_at=time.time(),actual_games=actual_games,actual_queries=actual_queries,seconds=time.monotonic()-start,source_sha256=Q.sha(O/'declaration.json')));status['complete']=True;save()
 except BaseException as ex:status.update(failure=dict(type=type(ex).__name__,message=str(ex)));save();raise
print('COMPLETE',actual_games,actual_queries,round(time.monotonic()-start,3),endpoints)
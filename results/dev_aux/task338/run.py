"""Bounded actual quantity/mate material optimization against fixed unit search."""
import json,time,sys,math,os,importlib.util
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();sp=importlib.util.spec_from_file_location('G338',R/'results/dev_aux/task335/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task338';assert not (O/'declaration.json').exists();Q.P.stop();D0=json.loads((R/'results/dev_aux/task335/declaration.json').read_bytes());pilot=json.loads((R/'results/dev_aux/task335/result.json').read_bytes());audit=json.loads((R/'results/dev_aux/task336/audit.json').read_bytes());assert pilot['complete'] and audit['complete'];D=dict(task_id='338',initials=D0['initials'],roots=D0['train_roots'],colors=D0['colors'],unit=D0['unit'],node_limit=1024,cap=24,max_rounds_per_initial=4,whole_fuse_seconds=1200,projected_upper_seconds=pilot['seconds']/48*(3*4*9*16),goal='TrueCHECKMATE ±32; actualruleDRAW 0; nonterminalH24 unweightednonkingdifference/15. Keep sign andquantitycontributionsseparate.',goal_revision='335 explicitlyallowed rule-drawquantity;338changesdrawto0followingDot. All48pilot havezero ruleDRAW, so reusematches338goalexactly; anyfutureDRAW uses0. Notrewrite335.',step='Basefirst, N/B/R/Q half/double nearestinteger tiesup, clip32..8192/P208/K0. Strictbestthenupdate, tiesretainfirst includingbase, stopfamilyfirstno strictgain. Atmost4rounds, no mandatoryrun tocap.',cost_decision='Pilot48games14.844s -> atmost1728logicalevaluations534.384s beforecache/plateau. Small337 alreadyhasdifferentpolicies at1024 and8192, no need budgetraise. 336showsmixedscore dominatedby1mate perinitial; deliberatelytestlimitedempiricaloptimization while explicitlynotclaimhumanprice. Fourroundmaxlowersthaninitialsixproposal toprobechangingNBRQ once each. No extension/fee/worker; independent8developmentroots onlyafter all endpointsfreeze; goal comparison not humanselection.',pilot_reuse=48,binary_sha256=D0['binary_sha256'],development_source_sha256=Q.sha(R/'results/dev_aux/task335/declaration.json'),scope='Threeexistinginitials, algorithmic8trainroots/bothcolors, fixedunitopponent/coldmode3+1024, 24halfply. No human-label input, penalty, candidatechoice or stopcriteria. Rootdistribution andobjectivechanged versus322; notsame-conditionreplication. 16 deterministiccellsnotIIDconfidence. All actual go+completegamesjournalled, cacheexactprice/root/color/node/cap/goal only.')
Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+1200;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(encoding='utf-8'),'configure272','exec'),env);configure=env['configure'];cache={};actual_games=actual_queries=reuses=0;rounds=[];endpoints={};status=dict(complete=False)
def key(w,ri,color):return tuple(w[k] for k in 'PNBRQK'),ri,color
for z in pilot['calls']:assert z['termination'] in ('CHECKMATE','UNKNOWN_CUTOFF');cache[key(z['weights'],z['root'],z['color'])]=dict(z,source='335')
def save():Q.write(O/'progress.json',dict(actual_games=actual_games,actual_queries=actual_queries,cache_reuses=reuses,unique_cases=len(cache),rounds=rounds,endpoints=endpoints,seconds=time.monotonic()-start,status=status))
eu=None
try:
 eu=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
 with (O/'games.jsonl').open('x',encoding='utf-8') as games,(O/'queries.jsonl').open('x',encoding='utf-8') as journal:
  def evaluate(w,name):
   global actual_games,actual_queries,reuses
   ec=None;rows=[]
   try:
    for ri,f in enumerate(D['roots']):
     for color in D['colors']:
      kk=key(w,ri,color)
      if kk in cache:row=cache[kk];reuses+=1
      else:
       Q.P.A.guard(deadline,Q.P.stop)
       if ec is None:ec=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
       journal.write(json.dumps(dict(event='game_start',name=name,root=ri,color=color,weights=w),separators=(',',':'))+'\n');journal.flush();row=dict(name=name,root=ri,source='338',**G.run_game(ec,eu,w,D['unit'],f,color,deadline,configure,journal));
       if row['termination'] not in ('CHECKMATE','UNKNOWN_CUTOFF'):row['fitness']='0'
       actual_games+=1;actual_queries+=len(row['search_records']);cache[kk]=row;games.write(json.dumps(row,separators=(',',':'))+'\n');games.flush();os.fsync(games.fileno())
      rows.append(row)
   finally:
    if ec:ec.close()
   v=sum(F(z['fitness']) for z in rows)/16;return v,dict(mate_sign_mean=str(F(sum(z['finite_mate_sign'] for z in rows),16)),quantity_mean=str(F(sum(z['quantity_difference'] for z in rows),16)),mate_contribution=str(F(sum(z['finite_mate_sign'] for z in rows)*32,16)),quantity_contribution=str(sum(F(z['fitness']) if z['finite_mate_sign']==0 else F(0) for z in rows)/16))
  for family,initial in D['initials'].items():
   current=initial.copy();history=[];ending='max_rounds'
   for generation in range(4):
    candidates=[('base',current)]
    for k in 'NBRQ':
     for sign in ('-','+'):
      w=current.copy();w[k]=max(32,min(8192,(w[k]+1)//2 if sign=='-' else w[k]*2));candidates.append((k+sign,w))
    scores=[]
    for variant,w in candidates:
     v,stats=evaluate(w,f'{family}-g{generation}-{variant}');scores.append((v,variant,w,stats));save()
    chosen=max(scores,key=lambda z:z[0]);rd=dict(family=family,generation=generation,starting=current,selected=chosen[1],weights=chosen[2],strict_gain=chosen[0]>scores[0][0],baseline_fitness=str(scores[0][0]),selected_fitness=str(chosen[0]),candidates=[dict(variant=nm,weights=w,fitness=str(v),**st) for v,nm,w,st in scores]);rounds.append(rd);history.append(rd);current=chosen[2].copy();save();print(family,generation,chosen[1],str(chosen[0]),actual_games,actual_queries,round(time.monotonic()-start,3),flush=True)
    if not rd['strict_gain']:ending='no_strict_coordinate_improvement';break
   endpoints[family]=dict(weights=current,rounds=len(history),ending=ending,fitness=history[-1]['selected_fitness']);save()
  Q.write(O/'endpoints.json',dict(complete=True,endpoints=endpoints,frozen_at=time.time(),actual_games=actual_games,actual_queries=actual_queries,seconds=time.monotonic()-start,source_sha256=Q.sha(O/'declaration.json')));status['complete']=True;save()
except BaseException as ex:status['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
finally:
 if eu:eu.close()
print('COMPLETE',actual_games,actual_queries,round(time.monotonic()-start,3),endpoints,flush=True)
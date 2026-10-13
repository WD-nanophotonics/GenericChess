import json,hashlib,time,sys,os,math
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task618';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());d.update(question='Doesactualshortestmatewithin12 objective changepricelearning cheaply underSAMEoriginalmaturecaller?',objective='WIN:+13-actualplies, LOSS:-13, DRAW/UNFINISHED:0; no quantity orreference',frozen_at=time.time(),fuse=600,scope='Newgoal premise after617actuallocalchoices: SAME52train20devfixedexposedroots,8train3eligibledevelopmentfamilies,2initials12predeterminedjointdirections/warm1024/random, originalc69d96c handSEE baseline not611prototype. All2newendpoints BEFOREanynewdevscores/reference; no oldfitextension orsource/human fitness/root/axis/model selection. Existinginitialdevactual599sources reused,onlynewendpointdevphysicalgames; nonindependent exposeddevelopment, generatorunitbias. Expectedunder3min/600wholewallfuse, noresultdependentextraepochs.');(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');assert json.loads((R/'results/dev_aux/task615/result.json').read_bytes())['status']=='PASS_ALL_PHYSICAL_QUAL_AND_PANEL'
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];train=[f for f in d['roots'] if f['phase']=='train'];dev=[f for f in d['roots'] if f['phase']=='development'];start=time.monotonic();deadline=start+600
save=lambda p,x:p.write_text(json.dumps(x,indent=2),encoding='utf-8')
def fast(g):return F(0) if g['termination']['winner'] is None else F(13-len(g['actions'])) if g['termination']['winner']==g['color'] else F(-13)
def batch(ctx,w,roots,qj,gj):
 G.stop();assert time.monotonic()<deadline;e=ControlledEngine(w,qj,'warm_game');ctx['acks'].append(dict(weights=list(w),prices=e.prices));save(ctx['folder']/'price_acks.json',ctx['acks']);refs=[];goals=[];physical=[];plies=[];terms=[]
 try:
  for f in roots:
   for c in [0,1]:
    e.begin_game();g=native_game(e,None,e.w,f,c,None,d,deadline);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());ctx['games']+=1;ctx['go']+=len(g['queries']);refs.append(dict(file=ctx['folder'].relative_to(R).as_posix()+'/games.jsonl',line=ctx['games']));goals.append(str(fast(g)));physical.append(g['goal']);plies.append(len(g['actions']));terms.append(g['termination'])
 finally:e.close()
 return dict(weights=list(w),objective='actual_shortest_mate12',mean_goal=str(sum(map(F,goals))/len(goals)),goals=goals,physical_mixed_goals=physical,actual_plies=plies,terminations=terms,sources=refs)
P=R/'results/dev_aux/task619';P.mkdir(exist_ok=True);assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);updates=[];endpoints=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for p in d['initial_profiles']:
  w=list(p['weights']);base=batch(ctx,w,train,qj,gj)
  for i,di in enumerate(d['directions'][p['name']]):
   sw=list(w);plus=list(w);minus=list(w)
   for a,s in zip(d['axes'],di):plus[a]=max(32,min(4096,math.floor(w[a]*math.exp(.25*s)+.5)));minus[a]=max(32,min(4096,math.floor(w[a]*math.exp(-.25*s)+.5)))
   cs=[base,batch(ctx,plus,train,qj,gj),batch(ctx,minus,train,qj,gj)];mu=[F(x['mean_goal']) for x in cs];best=max(range(3),key=lambda j:mu[j]);gain=mu[best]-mu[0]
   if gain>0:w=list(cs[best]['weights']);base=cs[best]
   else:best=0
   updates.append(dict(start=p['name'],iteration=i,direction=di,start_weights=sw,candidates=cs,selected_index=best,accepted_gain=str(gain),after_weights=list(w)));save(P/'progress.json',dict(games=ctx['games'],go=ctx['go'],updates=updates,seconds=time.monotonic()-start));print('fastfit',p['name'],i,str(gain),ctx['games'],round(time.monotonic()-start,1),flush=True)
  endpoints.append(dict(start=p['name'],initial=p['weights'],endpoint=list(w),iterations=12))
save(P/'endpoints.json',dict(declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),all_endpoints_before_development=True,endpoints=endpoints,updates=updates));save(P/'result.json',dict(status='FIT_COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],seconds=time.monotonic()-start,endpoints=endpoints));freeze=dict(before_any_new_development=True,endpoint_sha256=hashlib.sha256((P/'endpoints.json').read_bytes()).hexdigest(),seconds=time.monotonic()-start);save(O/'all_endpoints_frozen.json',freeze)
profiles=[]
for e in endpoints:
 w=e['endpoint']
 if not any(p['weights']==w for p in profiles):profiles.append(dict(weights=w,names=[]))
 next(p for p in profiles if p['weights']==w)['names'].append(e['start']+'-endpoint')
P=R/'results/dev_aux/task620';P.mkdir(exist_ok=True);assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);rows=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for p in profiles:rows.append(dict(names=p['names'],batch=batch(ctx,p['weights'],dev,qj,gj)))
save(P/'result.json',dict(status='COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],rows=rows,profiles=profiles,fit=json.loads((R/'results/dev_aux/task619/result.json').read_bytes()),endpoint_freeze=freeze,seconds=time.monotonic()-start,initial_development_source='599ALLoriginalsameparamsinitials rawphysicalgames reusednotcountnew',scope=d['scope']));print('FAST_COMPLETE',ctx['games'],ctx['go'],round(time.monotonic()-start,3),flush=True)
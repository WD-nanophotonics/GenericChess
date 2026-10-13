import json,hashlib,time,sys,os,math
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task670';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());frozen=json.loads((R/'results/dev_aux/task662/roots_frozen.json').read_bytes());d['roots']=frozen['roots'];d['seed_base']=2026110002;d['directions']={p['name']:[[int(i==j) for j in range(12)] for i in range(12)] for p in d['initial_profiles']};d['multipliers']=[1,.25,.5,2,4,8,16];d.update(question='Doesbroadonepass coordinategrid improvecheapquantityprice optimization comparedtojointlocaldirections?',objective='ALLterminal/draw/unfinished signedboard+handphysicalpiececount/19; NOterminalbonus, no candidateprice/reference',frozen_at=time.time(),fuse=600,scope='NEWoptimizationpremise:12native-ID-order one-axis grids [1,.25,.5,2,4,8,16], baselinefirst, SAMEquantity-only and662fullarmyroots. BOTHdirectionANDstepsize change, costs4672maxfit vs1600joint; notisolateddirection/fair-equalworkclaim. No reference/methodwinner selection; exposednewdev reused honestlyasdevelopment: NEW16train8devroots/24families,16train8developmentfamilies,2initials12predeterminedjointdirections/warm1024/random, originalc69d96c handSEE baseline not611prototype. All2newendpoints BEFOREanynewdevscores/reference; no oldfitextension orsource/human fitness/root/axis/model selection. Existinginitialdevactual599sources reused,onlynewendpointdevphysicalgames; nonindependent exposeddevelopment, generatorunitbias. Expectedunder3min/600wholewallfuse, noresultdependentextraepochs.');(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');assert json.loads((R/'results/dev_aux/task615/result.json').read_bytes())['status']=='PASS_ALL_PHYSICAL_QUAL_AND_PANEL'
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];train=[f for f in d['roots'] if f['phase']=='train'];dev=[f for f in d['roots'] if f['phase']=='development'];start=time.monotonic();deadline=start+600
save=lambda p,x:p.write_text(json.dumps(x,indent=2),encoding='utf-8')
def fast(g):return F(g['raw_quantity'],19)
def batch(ctx,w,roots,qj,gj):
 G.stop();assert time.monotonic()<deadline;e=ControlledEngine(w,qj,'warm_game');ctx['acks'].append(dict(weights=list(w),prices=e.prices));save(ctx['folder']/'price_acks.json',ctx['acks']);refs=[];goals=[];physical=[];plies=[];terms=[]
 try:
  for f in roots:
   for c in [0,1]:
    e.begin_game();g=native_game(e,None,e.w,f,c,None,d,deadline);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());ctx['games']+=1;ctx['go']+=len(g['queries']);refs.append(dict(file=ctx['folder'].relative_to(R).as_posix()+'/games.jsonl',line=ctx['games']));goals.append(str(fast(g)));physical.append(g['goal']);plies.append(len(g['actions']));terms.append(g['termination'])
 finally:e.close()
 return dict(weights=list(w),objective='actual_quantity_only12',mean_goal=str(sum(map(F,goals))/len(goals)),goals=goals,physical_mixed_goals=physical,actual_plies=plies,terminations=terms,sources=refs)
P=R/'results/dev_aux/task671';P.mkdir(exist_ok=True);assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);updates=[];endpoints=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for p in d['initial_profiles']:
  w=list(p['weights']);base=batch(ctx,w,train,qj,gj)
  for i,di in enumerate(d['directions'][p['name']]):
   sw=list(w);axis=d['axes'][i];cs=[base];unique={tuple(w):base}
   for multiplier in d['multipliers'][1:]:
    cand=list(w);cand[axis]=max(32,min(4096,math.floor(w[axis]*multiplier+.5)));key=tuple(cand)
    if key not in unique:unique[key]=batch(ctx,cand,train,qj,gj)
    cs.append(unique[key])
   mu=[F(x['mean_goal']) for x in cs];best=max(range(7),key=lambda j:mu[j]);gain=mu[best]-mu[0]
   if gain>0:w=list(cs[best]['weights']);base=cs[best]
   else:best=0
   updates.append(dict(start=p['name'],iteration=i,direction=di,axis=axis,multipliers=d["multipliers"],start_weights=sw,candidates=cs,selected_index=best,accepted_gain=str(gain),after_weights=list(w)));save(P/'progress.json',dict(games=ctx['games'],go=ctx['go'],updates=updates,seconds=time.monotonic()-start));print('fastfit',p['name'],i,str(gain),ctx['games'],round(time.monotonic()-start,1),flush=True)
  endpoints.append(dict(start=p['name'],initial=p['weights'],endpoint=list(w),iterations=12))
save(P/'endpoints.json',dict(declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),all_endpoints_before_development=True,endpoints=endpoints,updates=updates));save(P/'result.json',dict(status='FIT_COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],seconds=time.monotonic()-start,endpoints=endpoints));freeze=dict(before_any_new_development=True,endpoint_sha256=hashlib.sha256((P/'endpoints.json').read_bytes()).hexdigest(),seconds=time.monotonic()-start);save(O/'all_endpoints_frozen.json',freeze)
profiles=[dict(weights=list(p['weights']),names=[p['name']+'-initial']) for p in d['initial_profiles']]
for e in endpoints:
 w=e['endpoint']
 if not any(p['weights']==w for p in profiles):profiles.append(dict(weights=w,names=[]))
 next(p for p in profiles if p['weights']==w)['names'].append(e['start']+'-endpoint')
P=R/'results/dev_aux/task672';P.mkdir(exist_ok=True);assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);rows=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for p in profiles:rows.append(dict(names=p['names'],batch=batch(ctx,p['weights'],dev,qj,gj)))
save(P/'result.json',dict(status='COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],rows=rows,profiles=profiles,fit=json.loads((R/'results/dev_aux/task671/result.json').read_bytes()),endpoint_freeze=freeze,seconds=time.monotonic()-start,initial_development_source='ALLinitial/endpoints NEWphysical665 onfresh8developmentfamilies; no599reuse',scope=d['scope']));print('FAST_COMPLETE',ctx['games'],ctx['go'],round(time.monotonic()-start,3),flush=True)
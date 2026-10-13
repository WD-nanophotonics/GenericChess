import json,hashlib,time,sys,os,math,cshogi as C
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task720';old=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());roots=json.loads((R/'results/dev_aux/task717/roots_frozen.json').read_bytes())['roots'];d=dict(roots=roots,initial_profiles=old['initial_profiles'],axes=old['axes'],multipliers=[1,.25,.5,2,4,8,16],seed_bases=[2026128002,2026130002],cap=24,nodes=1024,executable_sha256=old['executable_sha256'],fuse_seconds=900,objective='Meanofphysicalquantity12/19 andquantity24/19 acrossTWOfullydisjointrandomdrawsets; ALLterminal/draw/unfinished, no candidate/sourceprices ormatebonus.',frozen_at=time.time(),question='Canmulti-draw/multi-shorthorizon feedback improvecheappricelearning transfer?',scope='NEW719mechanics-coverage premise/717sourceblind60ALLlegal16train8dev; initialsignedqtynotzero butcandidate-independent rootconstant; notoldfitextraepochs; onepass12native-ID-order coordinategrids baselinefirststrictpositive, max9344fit128devH24shortgames expected8-12min/900wholefuse. DifferentH/goal/RNG/rootcondition than670, notoldfitextension/equalcostorisolatedcausality. All2endpoints BEFOREanydevelopment/reference; ALLinitial/endpoints physicallyevaluatedonNEWdev. No human/sourcefitness/root/axis/model/stop selection; preserveallfailed/negative/unfinished, no primary/default/UI/newworkers/fees.')
train=[f for f in roots if f['phase']=='train'];dev=[f for f in roots if f['phase']=='development'];prefixes=[(seed+2*f['index']+c+(100 if f['phase']=='development' else 0))*100 for seed in d['seed_bases'] for f in roots for c in [0,1]];assert len(prefixes)==len(set(prefixes));assert len(train)==16 and len(dev)==8;assert json.loads((R/'results/dev_aux/task718/result.json').read_bytes())['status']=='PASS_ALL_DECLARED_ALLLEGAL_ROOTS_NATIVE';(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');start=time.monotonic();deadline=start+900
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];save=lambda p,x:p.write_text(json.dumps(x,indent=2),encoding='utf-8')
def qty12(g):
 b=C.Board(g['root']['initial_sfen'])
 for u in g['root']['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 for a in g['actions'][:12]:assert b.sfen()==a['before_sfen'];m=b.move_from_usi(a['move']);assert b.is_legal(m);b.push(m)
 n=[0,0]
 for pc in b.pieces:
  if pc and pc%16!=8:n[0 if pc<16 else 1]+=1
 for i,h in enumerate(b.pieces_in_hand):n[i]+=sum(h)
 assert sum(n)==38;return n[g['color']]-n[1-g['color']]
def batch(ctx,w,rr,qj,gj):
 G.stop();assert time.monotonic()<deadline;refs=[];goals=[];q12s=[];q24s=[];terms=[]
 for replica,seed in enumerate(d['seed_bases']):
  e=ControlledEngine(w,qj,'warm_game');ctx['acks'].append(dict(replica=replica,weights=e.w,prices=e.prices));save(ctx['folder']/'price_acks.json',ctx['acks'])
  try:
   for f in rr:
    for color in [0,1]:
     e.begin_game();g=native_game(e,None,e.w,f,color,None,dict(cap=24,nodes=1024,seed_base=seed),deadline);q12=qty12(g);q24=g['raw_quantity'];goal=F(q12+q24,38);g.update(replica=replica,seed_base=seed,cap=24,quantity12=q12,quantity24=q24,fitness=str(goal));gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());ctx['games']+=1;ctx['go']+=len(g['queries']);refs.append(dict(file=ctx['folder'].relative_to(R).as_posix()+'/games.jsonl',line=ctx['games']));goals.append(str(goal));q12s.append(q12);q24s.append(q24);terms.append(g['termination'])
  finally:e.close()
 return dict(weights=list(w),objective='actual_two_draw_quantity12_24',mean_goal=str(sum(map(F,goals))/len(goals)),goals=goals,quantity12=q12s,quantity24=q24s,terminations=terms,sources=refs)
P=R/'results/dev_aux/task721';P.mkdir(exist_ok=True);assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);updates=[];endpoints=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for initial in d['initial_profiles']:
  w=list(initial['weights']);base=batch(ctx,w,train,qj,gj)
  for iteration,axis in enumerate(d['axes']):
   sw=list(w);cs=[base];cache={tuple(w):base}
   for mult in d['multipliers'][1:]:
    cand=list(w);cand[axis]=max(32,min(4096,math.floor(w[axis]*mult+.5)));key=tuple(cand)
    if key not in cache:cache[key]=batch(ctx,cand,train,qj,gj)
    cs.append(cache[key])
   mu=[F(c['mean_goal']) for c in cs];best=max(range(7),key=lambda j:mu[j]);gain=mu[best]-mu[0]
   if gain>0:w=list(cs[best]['weights']);base=cs[best]
   else:best=0
   updates.append(dict(start=initial['name'],iteration=iteration,axis=axis,start_weights=sw,candidates=cs,selected_index=best,accepted_gain=str(gain),after_weights=list(w)));save(P/'progress.json',dict(games=ctx['games'],go=ctx['go'],updates=updates,seconds=time.monotonic()-start));print('multi_fit',initial['name'],axis,str(gain),ctx['games'],ctx['go'],round(time.monotonic()-start,1),flush=True)
  endpoints.append(dict(start=initial['name'],initial=initial['weights'],endpoint=list(w),iterations=12))
save(P/'endpoints.json',dict(declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),all_endpoints_before_development=True,endpoints=endpoints,updates=updates));save(P/'result.json',dict(status='FIT_COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],seconds=time.monotonic()-start,endpoints=endpoints));freeze=dict(before_any_new_development=True,endpoint_sha256=hashlib.sha256((P/'endpoints.json').read_bytes()).hexdigest());save(O/'all_endpoints_frozen.json',freeze)
profiles=[dict(weights=x['weights'],names=[x['name']+'-initial']) for x in d['initial_profiles']]
for e in endpoints:
 found=next((p for p in profiles if p['weights']==e['endpoint']),None)
 if found is None:found=dict(weights=e['endpoint'],names=[]);profiles.append(found)
 found['names'].append(e['start']+'-endpoint')
P=R/'results/dev_aux/task722';P.mkdir(exist_ok=True);assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);rows=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for p in profiles:rows.append(dict(names=p['names'],batch=batch(ctx,p['weights'],dev,qj,gj)))
save(P/'result.json',dict(status='COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],rows=rows,profiles=profiles,endpoint_freeze=freeze,seconds=time.monotonic()-start,scope=d['scope']));print('MULTI_COMPLETE',ctx['games'],ctx['go'],round(time.monotonic()-start,3),flush=True)

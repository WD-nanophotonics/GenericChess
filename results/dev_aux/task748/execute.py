import json,hashlib,time,sys,os,math,cshogi as C
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task748';assert json.loads((R/'results/dev_aux/task745/result.json').read_bytes())['status']=='PASS_ALL_FIXED_UNIT_SIGN_LEARNING_AND_DEV';old=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());roots=json.loads((R/'results/dev_aux/task740/roots_frozen.json').read_bytes())['roots'];assert json.loads((R/'results/dev_aux/task741/result.json').read_bytes())['status']=='PASS_ALL_DECLARED_ALLLEGAL_ROOTS_NATIVE';d=dict(roots=roots,initial_profiles=old['initial_profiles'],fixed_opponent=old['initial_profiles'][0]['weights'],axes=old['axes'],multipliers=[1,.25,.5,2,4,8,16],cap=12,development_cap=24,nodes=1024,seed_base=0,executable_sha256=old['executable_sha256'],fuse_seconds=900,frozen_at=time.time(),objective='Royal terminal at-or-before12 first win+1/loss-1/draw0 unchanged; otherwise quantity12/19 magnitude. Samefixedunit/H12caller as742, no price/ref fitness.',scope='747pairednonterminal-magnitude control AFTERAdevheadline exposed; SAME740root/opponent/H12/search/optimizer, allBendpoints beforeownBdev/reference. Exploratorynotblindmethodselection. Sameoriginaltwoinitials/onepass12native-order7grid/P90K0/free12bounds32..4096, max4672physicalfit+64physicaldev, expected5-10min/whole900fuse. Deterministicunit materialsearcher BOTHsides1024/warmgame/one thread16MiB, no fakeRNGreplication. ALLendpoints beforeNEWdev/reference. DevphysicalH24 retainsliteral12prefix/lateqty/fast/terminal; do notassumelearningtransfers. No human/sourcefitness/root/axis/model/stopselection; allnegative/failed/unfinished kept. Ownbranchonly/no primary/default/UI/workers/fees. Material-onlymodifiedYane finiteShogi, notunmodifiedNNUE/Stockfish/genericdomain.')
train=[f for f in roots if f['phase']=='train'];dev=[f for f in roots if f['phase']=='development'];assert len(train)==16 and len(dev)==8;save=lambda p,x:p.write_text(json.dumps(x,indent=2),encoding='utf-8');save(O/'declaration.json',d);start=time.monotonic();deadline=start+900
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256']
def quantity12(g):
 b=C.Board(g['root']['initial_sfen'])
 for u in g['root']['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 for a in g['actions'][:12]:assert b.sfen()==a['before_sfen'];m=b.move_from_usi(a['move']);assert b.is_legal(m);b.push(m)
 n=[0,0]
 for pc in b.pieces:
  if pc and pc%16!=8:n[0 if pc<16 else 1]+=1
 for side,h in enumerate(b.pieces_in_hand):n[side]+=sum(h)
 assert sum(n)==38;return n[g['color']]-n[1-g['color']]
def fitness(g,q12):
 if len(g['actions'])<=12 and not g['termination']['kind'].startswith('cap'):
  w=g['termination']['winner'];return F(0 if w is None else 1 if w==g['color'] else -1)
 return F(q12,19)
closed_cache={};closed=R/'results/dev_aux/task743';closed_ep=json.loads((closed/'endpoints.json').read_bytes());source_hash={name:hashlib.sha256((closed/name).read_bytes()).hexdigest() for name in ['games.jsonl','queries.jsonl','price_acks.json','endpoints.json','result.json']}
for u in closed_ep['updates']:
 for x in u['candidates']:
  z=dict(x);goals=[]
  for q,t in zip(x['quantity12'],x['terminations']):
   # original32cells root/color order; candidatecolor alternates0,1
   color=len(goals)%2;goals.append(str(F(q,19) if t['kind'].startswith('cap') else F(0 if t['winner'] is None else 1 if t['winner']==color else -1)))
  z.update(objective='terminal_first_else_quantitymagnitude12',goals=goals,mean_goal=str(sum(map(F,goals))/32),cached_original_sign_physical=True);closed_cache.setdefault(tuple(x['weights']),z)
save(O/'cached_source_manifest.json',dict(source_sha256=source_hash,unique_prices=len(closed_cache),scope='Fullsamevectors andcaller, goalsrecomputed quantity/19 vsoldsign; physicalnotnew, no olddecisions reused'))
def batch(ctx,w,rr,cap,qj,gj):
 if cap==12 and rr==train and tuple(w) in closed_cache:
  ctx['cache_hits']=ctx.get('cache_hits',0)+1;save(ctx['folder']/'cache_usage.json',dict(closed_source_batches=ctx['cache_hits'],cached_cells=32*ctx['cache_hits']));return closed_cache[tuple(w)]
 G.stop();assert time.monotonic()<deadline;e=ControlledEngine(w,qj,'warm_game');eu=ControlledEngine(d['fixed_opponent'],qj,'warm_game');ctx['acks'].extend([dict(role='candidate',weights=e.w,prices=e.prices),dict(role='unit',weights=eu.w,prices=eu.prices)]);save(ctx['folder']/'price_acks.json',ctx['acks']);refs=[];goals=[];quant12=[];quantfinal=[];terms=[]
 try:
  for f in rr:
   for color in [0,1]:
    e.begin_game();eu.begin_game();g=native_game(e,eu,e.w,f,color,None,dict(cap=cap,nodes=1024,seed_base=0),deadline);q12=quantity12(g);goal=fitness(g,q12);g.update(cap=cap,quantity12=q12,quantity24=g['raw_quantity'] if cap==24 else None,fitness=str(goal));gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());ctx['games']+=1;ctx['go']+=len(g['queries']);refs.append(dict(file=ctx['folder'].relative_to(R).as_posix()+'/games.jsonl',line=ctx['games']));goals.append(str(goal));quant12.append(q12);quantfinal.append(g['raw_quantity']);terms.append(g['termination'])
 finally:e.close();eu.close()
 return dict(weights=list(w),objective='terminal_first_else_quantitymagnitude12',mean_goal=str(sum(map(F,goals))/len(goals)),goals=goals,quantity12=quant12,quantity_final=quantfinal,terminations=terms,sources=refs)
P=R/'results/dev_aux/task749';assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);updates=[];endpoints=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for initial in d['initial_profiles']:
  w=list(initial['weights']);base=batch(ctx,w,train,12,qj,gj)
  for iteration,axis in enumerate(d['axes']):
   sw=list(w);cs=[base];cache={tuple(w):base}
   for mult in d['multipliers'][1:]:
    cand=list(w);cand[axis]=max(32,min(4096,math.floor(w[axis]*mult+.5)));key=tuple(cand)
    if key not in cache:cache[key]=batch(ctx,cand,train,12,qj,gj)
    cs.append(cache[key])
   mu=[F(x['mean_goal']) for x in cs];best=max(range(7),key=lambda j:mu[j]);gain=mu[best]-mu[0]
   if gain>0:w=list(cs[best]['weights']);base=cs[best]
   else:best=0
   updates.append(dict(start=initial['name'],iteration=iteration,axis=axis,start_weights=sw,candidates=cs,selected_index=best,accepted_gain=str(gain),after_weights=list(w)));save(P/'progress.json',dict(games=ctx['games'],go=ctx['go'],updates=updates,seconds=time.monotonic()-start));print('FIXED_FIT',initial['name'],axis,str(gain),ctx['games'],ctx['go'],round(time.monotonic()-start,1),flush=True)
  endpoints.append(dict(start=initial['name'],initial=initial['weights'],endpoint=w,iterations=12))
save(P/'endpoints.json',dict(declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),all_endpoints_before_development=True,endpoints=endpoints,updates=updates));save(P/'result.json',dict(status='FIT_COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],cached_source_batches=ctx.get('cache_hits',0),cached_cells=32*ctx.get('cache_hits',0),seconds=time.monotonic()-start,endpoints=endpoints));freeze=dict(before_any_new_development=True,endpoint_sha256=hashlib.sha256((P/'endpoints.json').read_bytes()).hexdigest());save(O/'all_endpoints_frozen.json',freeze)
profiles=[dict(weights=x['weights'],names=[x['name']+'-initial']) for x in d['initial_profiles']]
for e in endpoints:
 found=next((p for p in profiles if p['weights']==e['endpoint']),None)
 if found is None:found=dict(weights=e['endpoint'],names=[]);profiles.append(found)
 found['names'].append(e['start']+'-endpoint')
P=R/'results/dev_aux/task750';assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);rows=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for p in profiles:rows.append(dict(names=p['names'],batch=batch(ctx,p['weights'],dev,24,qj,gj)))
save(P/'result.json',dict(status='COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],rows=rows,profiles=profiles,endpoint_freeze=freeze,seconds=time.monotonic()-start,scope=d['scope']));print('FIXED_COMPLETE',ctx['games'],ctx['go'],round(time.monotonic()-start,3),flush=True)

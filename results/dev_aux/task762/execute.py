import json,hashlib,time,sys,os,math,cshogi as C
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task762';assert json.loads((R/'results/dev_aux/task751/result.json').read_bytes())['status']=='PASS_ALL_FIXED_UNIT_MAGNITUDE_CONTROL_CACHED_AND_NEW';old=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());roots=json.loads((R/'results/dev_aux/task740/roots_frozen.json').read_bytes())['roots'];assert json.loads((R/'results/dev_aux/task741/result.json').read_bytes())['status']=='PASS_ALL_DECLARED_ALLLEGAL_ROOTS_NATIVE';d=dict(roots=roots,initial_profiles=old['initial_profiles'],fixed_opponent=old['initial_profiles'][0]['weights'],axes=old['axes'],multipliers=[1,.25,.5,2,4,8,16],cap=12,development_cap=24,nodes=1024,seed_base=0,executable_sha256=old['executable_sha256'],fuse_seconds=900,frozen_at=time.time(),objective='Royal terminal at-or-before12 first: win+1/loss-1/draw0; otherwise sign(signed board+hand nonkingquantity12). No candidate/source/humanprice weightedfitness.',scope='761changed per-cell true-loss/win updateguard, SAME740/opponent/H12/sign, postA/Bdev exploratory; no newWDL guarantee. Sameoriginaltwoinitials/onepass12native-order7grid/P90K0/free12bounds32..4096, max4672physicalfit+64physicaldev, expected5-10min/whole900fuse. Deterministicunit materialsearcher BOTHsides1024/warmgame/one thread16MiB, no fakeRNGreplication. ALLendpoints beforeNEWdev/reference. DevphysicalH24 retainsliteral12prefix/lateqty/fast/terminal; do notassumelearningtransfers. No human/sourcefitness/root/axis/model/stopselection; allnegative/failed/unfinished kept. Ownbranchonly/no primary/default/UI/workers/fees. Material-onlymodifiedYane finiteShogi, notunmodifiedNNUE/Stockfish/genericdomain.')
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
 return F((q12>0)-(q12<0))
closed_cache={};closed_dev={};source_hash={}
for n in [743,749]:
 p=R/f'results/dev_aux/task{n}';source_hash[str(n)]={name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ['games.jsonl','queries.jsonl','price_acks.json','endpoints.json','result.json']}
 for u in json.loads((p/'endpoints.json').read_bytes())['updates']:
  for x in u['candidates']:
   z=dict(x);gg=[str(F((q>0)-(q<0)) if t['kind'].startswith('cap') else F(0 if t['winner'] is None else 1 if t['winner']==i%2 else -1)) for i,(q,t) in enumerate(zip(x['quantity12'],x['terminations']))];z.update(goals=gg,mean_goal=str(sum(map(F,gg))/32),objective='terminal_first_else_quantitysign12',cached_source_physical=True);closed_cache.setdefault(tuple(x['weights']),z)
for n in [744,750]:
 p=R/f'results/dev_aux/task{n}';source_hash[str(n)]={name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ['games.jsonl','queries.jsonl','price_acks.json','result.json']}
 for row in json.loads((p/'result.json').read_bytes())['rows']:
  x=row['batch'];z=dict(x)
  if n==750:
   gs=[json.loads(t) for t in (p/'games.jsonl').open(encoding='utf-8')];z['goals']=[str(fitness(gs[ref['line']-1],q)) for ref,q in zip(x['sources'],x['quantity12'])];z['mean_goal']=str(sum(map(F,z['goals']))/16)
  z.update(objective='terminal_first_else_quantitysign12',cached_source_physical=True);closed_dev.setdefault(tuple(z['weights']),z)
save(O/'cached_source_manifest.json',dict(source_sha256=source_hash,train_prices=len(closed_cache),dev_prices=len(closed_dev),scope='Exactmatchedphysicalsource only, signrecomputed, no olddecisions andnotNEWphysical'))
def states(c):
 return ['win' if t['winner']==i%2 else 'loss' if t['winner'] is not None else 'draw' if not t['kind'].startswith('cap') else 'unfinished' for i,t in enumerate(c['terminations'])]
def guard(base,c):
 aa=states(base);bb=states(c);return all(not(x!='loss' and y=='loss') and not(x=='win' and y!='win') for x,y in zip(aa,bb))
def batch(ctx,w,rr,cap,qj,gj):
 cc=closed_cache if cap==12 and rr==train else closed_dev if cap==24 and rr==dev else {}
 if tuple(w) in cc:
  ctx['cache_hits']=ctx.get('cache_hits',0)+1;save(ctx['folder']/'cache_usage.json',dict(closed_source_batches=ctx['cache_hits'],cached_cells=len(rr)*2*ctx['cache_hits']));return cc[tuple(w)]
 G.stop();assert time.monotonic()<deadline;e=ControlledEngine(w,qj,'warm_game');eu=ControlledEngine(d['fixed_opponent'],qj,'warm_game');ctx['acks'].extend([dict(role='candidate',weights=e.w,prices=e.prices),dict(role='unit',weights=eu.w,prices=eu.prices)]);save(ctx['folder']/'price_acks.json',ctx['acks']);refs=[];goals=[];quant12=[];quantfinal=[];terms=[]
 try:
  for f in rr:
   for color in [0,1]:
    e.begin_game();eu.begin_game();g=native_game(e,eu,e.w,f,color,None,dict(cap=cap,nodes=1024,seed_base=0),deadline);q12=quantity12(g);goal=fitness(g,q12);g.update(cap=cap,quantity12=q12,quantity24=g['raw_quantity'] if cap==24 else None,fitness=str(goal));gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());ctx['games']+=1;ctx['go']+=len(g['queries']);refs.append(dict(file=ctx['folder'].relative_to(R).as_posix()+'/games.jsonl',line=ctx['games']));goals.append(str(goal));quant12.append(q12);quantfinal.append(g['raw_quantity']);terms.append(g['termination'])
 finally:e.close();eu.close()
 return dict(weights=list(w),objective='terminal_first_else_quantitysign12',mean_goal=str(sum(map(F,goals))/len(goals)),goals=goals,quantity12=quant12,quantity_final=quantfinal,terminations=terms,sources=refs)
P=R/'results/dev_aux/task763';assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);updates=[];endpoints=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for initial in d['initial_profiles']:
  w=list(initial['weights']);base=batch(ctx,w,train,12,qj,gj)
  for iteration,axis in enumerate(d['axes']):
   sw=list(w);cs=[base];cache={tuple(w):base}
   for mult in d['multipliers'][1:]:
    cand=list(w);cand[axis]=max(32,min(4096,math.floor(w[axis]*mult+.5)));key=tuple(cand)
    if key not in cache:cache[key]=batch(ctx,cand,train,12,qj,gj)
    cs.append(cache[key])
   mu=[F(x['mean_goal']) for x in cs];feasible=[guard(cs[0],c) for c in cs];assert feasible[0];best=max([j for j in range(7) if feasible[j]],key=lambda j:mu[j]);gain=mu[best]-mu[0]
   if gain>0:w=list(cs[best]['weights']);base=cs[best]
   else:best=0
   updates.append(dict(start=initial['name'],iteration=iteration,axis=axis,start_weights=sw,candidates=cs,guard_feasible=feasible,selected_index=best,accepted_gain=str(gain),after_weights=list(w)));save(P/'progress.json',dict(games=ctx['games'],go=ctx['go'],updates=updates,seconds=time.monotonic()-start));print('FIXED_FIT',initial['name'],axis,str(gain),ctx['games'],ctx['go'],round(time.monotonic()-start,1),flush=True)
  endpoints.append(dict(start=initial['name'],initial=initial['weights'],endpoint=w,iterations=12))
save(P/'endpoints.json',dict(declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),all_endpoints_before_development=True,endpoints=endpoints,updates=updates));save(P/'result.json',dict(status='FIT_COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],cached_source_batches=ctx.get('cache_hits',0),cached_cells=32*ctx.get('cache_hits',0),seconds=time.monotonic()-start,endpoints=endpoints));freeze=dict(before_any_new_development=True,endpoint_sha256=hashlib.sha256((P/'endpoints.json').read_bytes()).hexdigest());save(O/'all_endpoints_frozen.json',freeze)
profiles=[dict(weights=x['weights'],names=[x['name']+'-initial']) for x in d['initial_profiles']]
for e in endpoints:
 found=next((p for p in profiles if p['weights']==e['endpoint']),None)
 if found is None:found=dict(weights=e['endpoint'],names=[]);profiles.append(found)
 found['names'].append(e['start']+'-endpoint')
P=R/'results/dev_aux/task764';assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);rows=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for p in profiles:rows.append(dict(names=p['names'],batch=batch(ctx,p['weights'],dev,24,qj,gj)))
save(P/'result.json',dict(status='COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],cached_source_batches=ctx.get('cache_hits',0),cached_cells=16*ctx.get('cache_hits',0),rows=rows,profiles=profiles,endpoint_freeze=freeze,seconds=time.monotonic()-start,scope=d['scope']));print('FIXED_COMPLETE',ctx['games'],ctx['go'],round(time.monotonic()-start,3),flush=True)

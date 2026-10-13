import json,hashlib,time,sys,os,math,cshogi as C
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task813';old=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());roots=json.loads((R/'results/dev_aux/task784/roots_frozen.json').read_bytes())['roots'];assert json.loads((R/'results/dev_aux/task785/result.json').read_bytes())['status']=='PASS_ALL_DECLARED_ALLLEGAL_ROOTS_NATIVE';d=dict(roots=roots,initial_profiles=old['initial_profiles'],fixed_opponent=old['initial_profiles'][0]['weights'],axes=old['axes'],multipliers=[1,.25,.5,2,4,8,16],cap=12,development_cap=24,nodes=256,seed_base=0,executable_sha256=old['executable_sha256'],fuse_seconds=1200,frozen_at=time.time(),objective='Selectionlex(-true_loss_count,true_win_count,meanroyalfirst quantity12/19). Per-cell terminalwin1/loss-1/draw0 elsequantity12/19. No human/sourcefitness.',scope='812quarter256nodesmixed2fixedopponent NEWprospectiveoriginalinitials lextraining. Samecaller mixedfixedopponents/256H12,12axes7gridbounds. AllF/Gendpoints before anyF/Gdev/reference; FconstructionpostD/Edev/reference, exploratory. Max1200wholefuse estimated6-9min, material-onlymodifiedYane standardShogi only; allnegatives/failures kept.')
train=[f for f in roots if f['phase']=='train'];dev=[f for f in roots if f['phase']=='development'];assert len(train)==16 and len(dev)==8;save=lambda p,x:p.write_text(json.dumps(x,indent=2),encoding='utf-8');save(O/'declaration.json',d);start=time.monotonic();deadline=start+1200
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];d['opponents']={x['name']:x['weights'] for x in old['initial_profiles']};save(O/'declaration.json',d)
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
def batch_key(c):
 t=c['terminations'];loss=sum(not x['kind'].startswith('cap') and x['winner'] is not None and x['winner']!=i%2 for i,x in enumerate(t));win=sum(not x['kind'].startswith('cap') and x['winner']==i%2 for i,x in enumerate(t));return (-loss,win,F(c['mean_goal']))
closed_unit={};save(O/'cached_source_manifest.json',dict(source_sha256={},unit_prices=0,scope='NONE: different256node budget, old1024cache noteligible'))
closed_mixed={}
def batch(ctx,w,rr,cap,qj,gj):
 if tuple(w) in closed_mixed:return closed_mixed[tuple(w)]
 goals=[];q12s=[];qfinal=[];terms=[];refs=[]
 for opponent,oppw in d['opponents'].items():
  if opponent=='unit' and tuple(w) in closed_unit:
   c=closed_unit[tuple(w)];goals+=c['goals'];q12s+=c['quantity12'];qfinal+=c['quantity_final'];terms+=c['terminations'];refs+=c['sources'];ctx['cache_hits']=ctx.get('cache_hits',0)+1;save(ctx['folder']/'cache_usage.json',dict(unit32_source_batches=ctx['cache_hits'],cached_cells=32*ctx['cache_hits']));continue
  G.stop();assert time.monotonic()<deadline;e=ControlledEngine(w,qj,'warm_game');eu=ControlledEngine(oppw,qj,'warm_game');ctx['acks'].extend([dict(role='candidate',opponent=opponent,weights=e.w,prices=e.prices),dict(role='unit',opponent=opponent,weights=eu.w,prices=eu.prices)]);save(ctx['folder']/'price_acks.json',ctx['acks'])
  try:
   for f in rr:
    for color in [0,1]:
     e.begin_game();eu.begin_game();g=native_game(e,eu,e.w,f,color,None,dict(cap=cap,nodes=256,seed_base=0),deadline);q=quantity12(g);fit=fitness(g,q);g.update(opponent=opponent,cap=cap,quantity12=q,quantity24=None,fitness=str(fit));gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());ctx['games']+=1;ctx['go']+=len(g['queries']);refs.append(dict(file=ctx['folder'].relative_to(R).as_posix()+'/games.jsonl',line=ctx['games']));goals.append(str(fit));q12s.append(q);qfinal.append(g['raw_quantity']);terms.append(g['termination'])
  finally:e.close();eu.close()
 assert len(goals)==64;c=dict(weights=list(w),objective='terminal_first_else_quantitymagnitude12',mean_goal=str(sum(map(F,goals))/64),goals=goals,quantity12=q12s,quantity_final=qfinal,terminations=terms,sources=refs);closed_mixed[tuple(w)]=c;return c
P=R/'results/dev_aux/task814';assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);updates=[];endpoints=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for initial in d['initial_profiles']:
  w=list(initial['weights']);base=batch(ctx,w,train,12,qj,gj)
  for iteration,axis in enumerate(d['axes']):
   sw=list(w);cs=[base];cache={tuple(w):base}
   for mult in d['multipliers'][1:]:
    cand=list(w);cand[axis]=max(32,min(4096,math.floor(w[axis]*mult+.5)));key=tuple(cand)
    if key not in cache:cache[key]=batch(ctx,cand,train,12,qj,gj)
    cs.append(cache[key])
   mu=[batch_key(x) for x in cs];best=max(range(7),key=lambda j:mu[j]);gain=F(cs[best]['mean_goal'])-F(cs[0]['mean_goal']);accepted=mu[best]>mu[0]
   if accepted:w=list(cs[best]['weights']);base=cs[best]
   else:best=0
   updates.append(dict(start=initial['name'],iteration=iteration,axis=axis,start_weights=sw,candidates=cs,selected_index=best,accepted_gain=str(gain),lex_keys=[[z[0],z[1],str(z[2])] for z in mu],accepted=accepted,after_weights=list(w)));save(P/'progress.json',dict(games=ctx['games'],go=ctx['go'],updates=updates,seconds=time.monotonic()-start));print('FIXED_FIT',initial['name'],axis,str(gain),ctx['games'],ctx['go'],round(time.monotonic()-start,1),flush=True)
  endpoints.append(dict(start=initial['name'],initial=initial['weights'],endpoint=w,iterations=12))
save(P/'endpoints.json',dict(declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),all_endpoints_before_development=True,endpoints=endpoints,updates=updates));save(P/'result.json',dict(status='FIT_COMPLETE',actual_games=ctx['games'],actual_go=ctx['go'],cached_source_batches=ctx.get('cache_hits',0),cached_cells=32*ctx.get('cache_hits',0),seconds=time.monotonic()-start,endpoints=endpoints));freeze=dict(before_any_new_development=True,endpoint_sha256=hashlib.sha256((P/'endpoints.json').read_bytes()).hexdigest());save(O/'all_endpoints_frozen.json',freeze)

print('LEX_FIT_CLOSED',ctx['games'],ctx['go'],round(time.monotonic()-start,3),flush=True)

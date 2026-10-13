import json,hashlib,time,sys,os,math,cshogi as C
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task700';old=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());roots=json.loads((R/'results/dev_aux/task675/roots_frozen.json').read_bytes())['roots'];d=json.loads((O/'declaration.json').read_bytes());d.update(roots=roots,initial_profiles=old['initial_profiles'],executable_sha256=old['executable_sha256']);assert json.loads((R/'results/dev_aux/task697/result.json').read_bytes())['status']=='PASS_ALL_PAIRED_H12_CONTROL_CACHED_AND_NEW'

train=[f for f in roots if f['phase']=='train'];dev=[f for f in roots if f['phase']=='development'];prefixes=[(seed+2*f['index']+c+(100 if f['phase']=='development' else 0))*100 for seed in d['seed_bases'] for f in roots for c in [0,1]];assert len(prefixes)==len(set(prefixes));assert len(roots)==16;assert json.loads((R/'results/dev_aux/task691/result.json').read_bytes())['status']=='ALL384_MULTI_HORIZON_FITNESS_PREFIX_PASS';(O/'execution_inputs.json').write_text(json.dumps(d,indent=2),encoding='utf-8');start=time.monotonic();deadline=start+600
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

profiles=[]
def add(w,name):
 found=next((p for p in profiles if p['weights']==w),None)
 if found is None:found=dict(weights=list(w),names=[]);profiles.append(found)
 found['names'].append(name)
for x in d['initial_profiles']:add(x['weights'],x['name']+'-initial')
for task,label in [(686,'A'),(695,'B')]:
 for e in json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())['endpoints']:
  name=label+'-'+e['start'];add(e['endpoint'],name+'-endpoint')
  for axis in d['axes']:
   w=list(e['endpoint']);w[axis]=e['initial'][axis];add(w,name+'-rollback-'+str(axis))
save(O/'all_profiles_frozen.json',dict(profiles=profiles,before_any_new_probes=True,maximum_games=64*len(profiles),source_endpoints_sha256={str(n):hashlib.sha256((R/f'results/dev_aux/task{n}/endpoints.json').read_bytes()).hexdigest() for n in [686,695]}));assert 64*len(profiles)<=3456
P=R/'results/dev_aux/task701';assert not(P/'games.jsonl').exists();ctx=dict(folder=P,games=0,go=0,acks=[]);rows=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for p in profiles:
  rows.append(dict(names=p['names'],batch=batch(ctx,p['weights'],roots,qj,gj)));save(P/'progress.json',dict(actual_games=ctx['games'],actual_go=ctx['go'],rows=rows,seconds=time.monotonic()-start));print('ROLLBACK',p['names'],ctx['games'],ctx['go'],round(time.monotonic()-start,1),flush=True)
save(P/'result.json',dict(status='COMPLETE_ALL_AXIS_ROLLBACKS',actual_games=ctx['games'],actual_go=ctx['go'],profiles=profiles,rows=rows,seconds=time.monotonic()-start,scope=d['scope']));print('ROLLBACK_COMPLETE',ctx['games'],ctx['go'],round(time.monotonic()-start,3),flush=True)

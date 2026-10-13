import json,sys,time,os,math,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task855';O.mkdir(exist_ok=False);start=time.monotonic();deadline=start+900
for n in [360,364,381,509,583,835,851]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from game_barrier_engine import GameBarrierEngine
from controller_reduced import native_game
assert json.loads((R/'results/dev_aux/task854/result.json').read_bytes())['status']=='PASS_ALL40_REDUCED_ROOTS_AND64_PILOT_GAMES';A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';d=json.loads((R/'results/dev_aux/task850/plan.json').read_bytes());d['seed_base']=2026142500;roots=json.loads((R/'results/dev_aux/task853/execution_inputs.json').read_bytes())['roots'];profiles=json.loads((R/'results/dev_aux/task853/execution_inputs.json').read_bytes())['profiles'];unit=[0]+[90]*7+[0]+[90]*6+[0];old=[json.loads(l) for l in (R/'results/dev_aux/task853/games.jsonl').open(encoding='utf-8')];updates=[];endpoints=[];acks=[];games=go=0;cache_sha=hashlib.sha256((R/'results/dev_aux/task853/games.jsonl').read_bytes()).hexdigest()
def value(g):
 t=g['termination'];v=0 if t['kind'].startswith('cap') or t['winner'] is None else 1 if t['winner']==g['color'] else -1;return F(v),F(25-len(g['actions']),25) if v>0 else F(-1) if v<0 else F(0)
def batch(w,variant,qj,gj):
 global games,go
 rr=[f for f in roots if f['variant']==variant];cells=[(opp,f,c) for opp in d['opponents'] for f in rr for c in [0,1]];cached=[(i+1,g) for i,g in enumerate(old) if g['weights']==w and g['root']['variant']==variant]
 if len(cached)==len(cells):
  assert [(g['opponent'],g['root'],g['color']) for _,g in cached]==cells;gs=[g for _,g in cached];refs=[dict(file='task853/games.jsonl',line=i) for i,_ in cached];new=False
 else:
  gs=[];refs=[];e=GameBarrierEngine(w,qj,'warm_game');eu=GameBarrierEngine(unit,qj,'warm_game');acks.extend([dict(weights=e.w,prices=e.prices),dict(weights=eu.w,prices=eu.prices)])
  try:
   for opp,f,c in cells:
    e.begin_game();eu.begin_game();g=native_game(e,eu if opp=='unit_search' else None,w,f,c,None,d,deadline);qj.flush();os.fsync(qj.fileno());g.update(opponent=opp,pool='train',cap=24);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());games+=1;go+=len(g['queries']);gs.append(g);refs.append(dict(file='task855/games.jsonl',line=games))
  finally:qj.flush();os.fsync(qj.fileno());e.close();eu.close()
  new=True
 vv=[value(g) for g in gs];mean=[sum(v[i] for v in vv)/len(vv) for i in [0,1]];return dict(weights=w,sources=refs,mean=[str(v) for v in mean],cells=len(vv),new_physical=new,terminal_counts=dict(win=sum(v[0]>0 for v in vv),loss=sum(v[0]<0 for v in vv),censored=sum(g['termination']['kind'].startswith('cap') for g in gs),draw=sum(not g['termination']['kind'].startswith('cap') and g['termination']['winner'] is None for g in gs)))
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for variant in ['NR','NRB']:
  for p in profiles:
   w=list(p['weights'])
   for axis in [6]+([5] if variant=='NRB' else []):
    candidates=[]
    for factor in [1,.25,.5,2,4,8,16]:
     v=list(w);v[axis]=v[axis+8]=max(32,min(4096,math.floor(w[axis]*factor+.5)));candidates.append(batch(v,variant,qj,gj))
    best=max(range(7),key=lambda i:tuple(F(v) for v in candidates[i]['mean']));u=dict(variant=variant,start=p['name'],axis=axis,start_weights=w,candidates=candidates,selected_index=best,after_weights=candidates[best]['weights']);updates.append(u);w=list(u['after_weights']);print('REAL_FIT',variant,p['name'],axis,best,w[5:7],candidates[best]['mean'],flush=True)
   endpoints.append(dict(name=variant+'_'+p['name'],variant=variant,start=p['name'],initial=p['weights'],endpoint=w))
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');result=dict(status='ALL4_REDUCED_TRUE_TERMINAL_ENDPOINTS_FROZEN',endpoints=endpoints,updates=updates,actual_new_games=games,actual_go=go,seconds=time.monotonic()-start,qualified_cache_source_sha256=cache_sha,scope='42logical7pointcandidatebatches acrossNR/NRB2initials, 6coordinateupdates. Realterminal contribution thenfastterminal, noquantityfitness. ALLcandidates/base-firstties; qualifiedinitialpilotcacheonly, otherphysicalrepeatskept. Endpointfreeze beforeholdout/reference. Reducedinventory+promotedtiesscopeonly.');(O/'endpoints.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('ALL_REDUCED_FIT',games,go,round(result['seconds'],3))

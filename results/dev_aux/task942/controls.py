import json,time,sys,os,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task943';O.mkdir(exist_ok=False);start=time.monotonic();deadline=start+180
for n in [360,364,381,509,583,835,851,901]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from game_barrier_engine import GameBarrierEngine
from controller_cooperation import native_game
assert json.loads((R/'results/dev_aux/task939/result.json').read_bytes())['status']=='PASS_ALL352_STOCK_EDGE_HELDOUT_GAMES'
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';p=json.loads((R/'results/dev_aux/task942/plan.json').read_bytes());u=[0]+[90]*7+[0]+[90]*6+[0];acks=[];n=go=0
(O/'execution_inputs.json').write_text(json.dumps(dict(plan=p,fixed_opponent=u),indent=2),encoding='utf-8')
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for cap,nodes in p['conditions']:
  if [cap,nodes]==p['cached_condition']:continue
  d=dict(cap=cap,nodes=nodes,seed_base=p['seed_base'])
  for v in p['profiles']:
   w=list(u);w[5]=w[13]=v;e=GameBarrierEngine(w,qj,'warm_game');eu=GameBarrierEngine(u,qj,'warm_game');acks.extend([dict(weights=e.w,prices=e.prices),dict(weights=eu.w,prices=eu.prices)])
   try:
    for opp in p['opponents']:
     for f in p['roots']:
      for c in [0,1]:
       e.begin_game();eu.begin_game();g=native_game(e,eu if opp=='unit_search' else None,w,f,c,None,d,deadline);qj.flush();os.fsync(qj.fileno());g.update(profile='B'+str(v),opponent=opp,pool=f['phase'],cap=cap,nodes=nodes);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());n+=1;go+=len(g['queries'])
   finally:qj.flush();os.fsync(qj.fileno());e.close();eu.close()
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');out=dict(status='ALL_FROZEN_HORIZON_CONTROLS_CLOSED',actual_games=n,actual_go=go,seconds=time.monotonic()-start);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)

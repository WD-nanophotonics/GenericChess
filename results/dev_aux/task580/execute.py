import sys,json,time,hashlib,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task580';d=json.loads((O/'declaration.json').read_bytes());assert not(O/'games.jsonl').exists()
for n in [360,364,381,509,547]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task564'));from controller12 import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];t0=time.monotonic();rows=[];acks=[];go=0
with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
 eu=ControlledEngine(d['fixed_opponent'],qj,'warm_game');acks.append(dict(role='unit',weights=eu.w,prices=eu.prices))
 try:
  for pi,p in enumerate(d['profiles']):
   G.stop();assert time.monotonic()-t0<600;ec=ControlledEngine(p['weights'],qj,'warm_game');acks.append(dict(role='candidate',profile=pi,weights=ec.w,prices=ec.prices));(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8')
   try:
    for opp in d['opponents']:
     for f in d['roots']:
      for c in d['colors']:
       ec.begin_game();eu.begin_game() if opp=='unit' else None;g=native_game(ec,eu if opp=='unit' else None,ec.w,f,c,None,d,t0+600);g.update(profile=pi,opponent=opp);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());go+=len(g['queries']);rows.append(dict(profile=pi,opponent=opp,root_index=f['index'],root_seed=f['seed'],color=c,source=dict(file='results/dev_aux/task580/games.jsonl',line=len(rows)+1),goal=g['goal'],quantity=g['raw_quantity'],termination=g['termination'],plies=len(g['actions']),query_count=len(g['queries'])))
   finally:ec.close()
   (O/'progress.json').write_text(json.dumps(dict(games=len(rows),actual_go=go,seconds=time.monotonic()-t0)),encoding='utf-8');print(pi,p['name'],len(rows),round(time.monotonic()-t0,1),flush=True)
 finally:eu.close()
out=dict(status='COMPLETE',actual_games=len(rows),actual_go=go,rows=rows,price_acks=acks,seconds=time.monotonic()-t0,scope=d['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');assert len(rows)==1000;print({k:v for k,v in out.items() if k not in ['rows','price_acks']})

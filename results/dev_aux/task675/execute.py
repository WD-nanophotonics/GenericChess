import json,hashlib,time,sys,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task675';d=json.loads((O/'deployment_declaration.json').read_bytes());P=R/'results/dev_aux/task676';P.mkdir(exist_ok=True);assert not(P/'games.jsonl').exists();start=time.monotonic();deadline=start+d['fuse_seconds']
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];acks=[];rows=[];go=0
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for replica,seed in enumerate(d['seed_bases']):
  for pi,p in enumerate(d['profiles']):
   G.stop();assert time.monotonic()<deadline;e=ControlledEngine(p['weights'],qj,'warm_game');acks.append(dict(replica=replica,profile=pi,weights=e.w,prices=e.prices));(P/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8')
   try:
    for f in d['roots']:
     for c in [0,1]:
      e.begin_game();g=native_game(e,None,e.w,f,c,None,dict(cap=24,nodes=1024,seed_base=seed),deadline);g.update(replica=replica,seed_base=seed,profile=pi,cap=24);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());go+=len(g['queries']);rows.append(dict(replica=replica,profile=pi,root=f['index'],color=c,source=dict(file='results/dev_aux/task676/games.jsonl',line=len(rows)+1)))
   finally:e.close()
   (P/'progress.json').write_text(json.dumps(dict(actual_games=len(rows),actual_go=go,replica=replica,profile=pi,seconds=time.monotonic()-start)),encoding='utf-8');print('rngprobe',replica,pi,len(rows),go,round(time.monotonic()-start,1),flush=True)
assert len(rows)==d['expected_physical_games'];out=dict(status='ALL_FROZEN_CONTEXT_RNG_PROBES_COMPLETE',actual_games=len(rows),actual_go=go,profiles=d['profiles'],rows=rows,seconds=time.monotonic()-start,declaration_sha256=hashlib.sha256((O/'deployment_declaration.json').read_bytes()).hexdigest(),scope=d['scope']);(P/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('ALL_RNG_COMPLETE',len(rows),go,round(time.monotonic()-start,3))

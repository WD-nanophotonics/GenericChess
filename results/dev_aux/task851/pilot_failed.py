import json,time,sys,os,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task852';O.mkdir(exist_ok=False);start=time.monotonic();deadline=start+180
for n in [360,364,381,509,583,835,851]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from game_barrier_engine import GameBarrierEngine
from controller_reduced import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';d=json.loads((R/'results/dev_aux/task850/plan.json').read_bytes());d['seed_base']=2026142500;roots=[r for r in json.loads((R/'results/dev_aux/task850/roots_frozen.json').read_bytes())['roots'] if r['phase']=='train'];u=[0]+[90]*7+[0]+[90]*6+[0];rw=list(u);rw[6]=rw[14]=126;rw[5]=rw[13]=328;profiles=[dict(name='unit',weights=u),dict(name='random_ratio',weights=rw)];acks=[];n=go=0;rows=[]
(O/'execution_inputs.json').write_text(json.dumps(dict(profiles=profiles,fixed_opponent=u,roots=roots,nodes=256,cap=24,seed_base=d['seed_base'],scope=d['variants']),indent=2),encoding='utf-8')
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for p in profiles:
  for opp in d['opponents']:
   e=GameBarrierEngine(p['weights'],qj,'warm_game');eu=GameBarrierEngine(u,qj,'warm_game') if opp=='unit_search' else None;acks.append(dict(weights=e.w,prices=e.prices));
   if eu:acks.append(dict(weights=eu.w,prices=eu.prices))
   try:
    for f in roots:
     for c in [0,1]:
      e.begin_game()
      if eu:eu.begin_game()
      g=native_game(e,eu,e.w,f,c,None,d,deadline);qj.flush();os.fsync(qj.fileno());g.update(profile=p['name'],opponent=opp,pool='train',cap=24);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());n+=1;go+=len(g['queries']);rows.append(dict(profile=p['name'],variant=f['variant'],opponent=opp,seed=f['seed'],color=c,termination=g['termination'],plies=len(g['actions'])))
   finally:qj.flush();os.fsync(qj.fileno());e.close();
   if eu:eu.close()
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');out=dict(status='ALL_REDUCED_TRAIN_INITIAL_PILOT_CLOSED',actual_games=n,actual_go=go,seconds=time.monotonic()-start,rows=rows,source_executable_sha256=hashlib.sha256(A.EXE.read_bytes()).hexdigest());(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('REDUCED_PILOT',n,go,round(out['seconds'],3));print('TRUE',sum(not r['termination']['kind'].startswith('cap') for r in rows),'CAP',sum(r['termination']['kind'].startswith('cap') for r in rows))
